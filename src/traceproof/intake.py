"""Application operations shared by the CLI and a future HTTP adapter."""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from traceproof.artifacts import ArtifactStore, open_scoped_source
from traceproof.domain import IntakeSpec, ItemState, RunState, TraceProofError
from traceproof.persistence import ImportBatch, ImportItem, Repository, Run, Snapshot, Store

MAX_CSV_BYTES = 1024 * 1024
MAX_ROWS = 1000


def now() -> str:
    return datetime.now(UTC).isoformat()


def submit(store: Store, csv_path: Path, input_root: Path, key: str) -> str:
    if not key.strip() or len(key) > 200:
        raise TraceProofError("Idempotency key must contain 1–200 characters")
    root = input_root.resolve(strict=True)
    if not root.is_dir():
        raise TraceProofError("Input root must be a directory")
    with csv_path.open("rb") as source:
        raw = source.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise TraceProofError("CSV exceeds 1 MiB limit")
    request_hash = hashlib.sha256(raw + b"\x00" + str(root).encode()).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        headers = reader.fieldnames
        required = {"repo_id", "source_type", "source_uri", "owner", "classification"}
        if not headers or len(headers) != len(set(headers)):
            raise TraceProofError("CSV must have unique column names")
        if not required.issubset(headers) or not set(headers).issubset(IntakeSpec.model_fields):
            raise TraceProofError(
                "CSV columns must include repo_id, source_type, source_uri, owner, classification; "
                "only sha256 and scan_profile are optional in this slice"
            )
        rows = []
        for number, row in enumerate(reader, start=2):
            if len(rows) >= MAX_ROWS:
                raise TraceProofError("CSV exceeds 1,000 data rows")
            rows.append((number, row))
        if not rows:
            raise TraceProofError("CSV has no data rows")
    except (UnicodeError, csv.Error) as exc:
        raise TraceProofError("CSV must be valid UTF-8 with well-formed quoted fields") from exc

    try:
        with store.transaction() as session:
            existing = session.scalar(select(ImportBatch).where(ImportBatch.idempotency_key == key))
            if existing is not None:
                if existing.request_sha256 != request_hash:
                    raise TraceProofError(
                        "Idempotency key was already used for a different request"
                    )
                return existing.id
            batch = ImportBatch(
                id=str(uuid4()),
                idempotency_key=key,
                request_sha256=request_hash,
                input_root=str(root),
                created_at=now(),
            )
            session.add(batch)
            session.flush()
            for number, row in rows:
                spec = None
                error = None
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise TraceProofError("CSV row has a different field count from its header")
                    normalized = {k: v for k, v in row.items() if v.strip()}
                    spec = IntakeSpec.model_validate(normalized)
                    with open_scoped_source(spec.source_uri, root):
                        pass
                    repo = session.get(Repository, spec.repo_id)
                    if repo is not None and (repo.owner, repo.classification) != (
                        spec.owner,
                        spec.classification,
                    ):
                        raise TraceProofError(
                            "Repository metadata conflicts with its existing registration"
                        )
                    if repo is None:
                        session.add(
                            Repository(
                                id=spec.repo_id,
                                owner=spec.owner,
                                classification=spec.classification,
                            )
                        )
                        session.flush()
                except ValidationError as exc:
                    # Do not echo arbitrary row values (which could contain credentials).
                    error = "; ".join(
                        f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
                        for item in exc.errors(include_input=False, include_url=False)
                    )
                except TraceProofError as exc:
                    error = str(exc)
                except OSError:
                    error = "Source is unavailable, not regular, or contains a symbolic link"
                run_id = None
                if error is None and spec is not None:
                    run_id = str(uuid4())
                    session.add(
                        Run(
                            id=run_id,
                            repo_id=spec.repo_id,
                            state=RunState.ADMITTED,
                            profile=spec.scan_profile,
                            created_at=now(),
                        )
                    )
                    session.flush()
                session.add(
                    ImportItem(
                        id=str(uuid4()),
                        import_id=batch.id,
                        row_number=number,
                        state=ItemState.REJECTED if error else ItemState.READY,
                        spec=spec.model_dump(mode="json") if error is None else None,
                        run_id=run_id,
                        error=error,
                        attempts=0,
                    )
                )
            return batch.id
    except IntegrityError:
        # Another submitter may have won the idempotency-key insert race.
        with store.transaction() as session:
            existing = session.scalar(select(ImportBatch).where(ImportBatch.idempotency_key == key))
            if existing is not None and existing.request_sha256 == request_hash:
                return existing.id
        raise TraceProofError("Concurrent import conflict; retry with the same key") from None


def import_status(store: Store, import_id: str) -> dict:
    with store.transaction() as session:
        batch = session.get(ImportBatch, import_id)
        if batch is None:
            raise TraceProofError("Import not found")
        items = session.scalars(
            select(ImportItem)
            .where(ImportItem.import_id == import_id)
            .order_by(ImportItem.row_number)
        ).all()
        return {
            "schema_version": "1",
            "import_id": import_id,
            "created_at": batch.created_at,
            "items": [
                {
                    "item_id": item.id,
                    "row_number": item.row_number,
                    "state": item.state,
                    "run_id": item.run_id,
                    "error": item.error,
                    "attempts": item.attempts,
                }
                for item in items
            ],
        }


def run_status(store: Store, run_id: str) -> dict:
    from traceproof.indexing import VERSION
    from traceproof.persistence import SourceIndex

    with store.transaction() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise TraceProofError("Run not found")
        index = (
            session.scalar(
                select(SourceIndex).where(
                    SourceIndex.snapshot_id == run.snapshot_id, SourceIndex.version == VERSION
                )
            )
            if run.snapshot_id
            else None
        )
        return {
            "schema_version": "1",
            "run_id": run.id,
            "repo_id": run.repo_id,
            "state": run.state,
            "profile": run.profile,
            "snapshot_id": run.snapshot_id,
            "analysis_performed": False,
            "report_status": "not_available",
            "index_status": index.state if index else "not_started",
            "coverage_report_status": "available" if index and index.report else "not_available",
            "message": "Security analysis and vulnerability reports are not implemented",
        }


def process(store: Store, artifacts: ArtifactStore, import_id: str, max_items: int = 1000) -> dict:
    """Caller must hold exclusive_worker. Persist before/after every filesystem stage."""
    with store.transaction() as session:
        batch = session.get(ImportBatch, import_id)
        if batch is None:
            raise TraceProofError("Import not found")
        root = Path(batch.input_root)
        interrupted = session.scalars(
            select(ImportItem).where(
                ImportItem.import_id == import_id, ImportItem.state == ItemState.PROCESSING
            )
        ).all()
        for item in interrupted:
            item.state = ItemState.READY if item.attempts < 3 else ItemState.FAILED
            item.error = (
                "Recovered interrupted intake"
                if item.attempts < 3
                else "Intake interrupted three times"
            )
            if item.attempts >= 3:
                session.get(Run, item.run_id).state = RunState.FAILED

    for _ in range(max_items):
        with store.transaction() as session:
            item = session.scalar(
                select(ImportItem)
                .where(ImportItem.import_id == import_id, ImportItem.state == ItemState.READY)
                .order_by(ImportItem.row_number)
                .limit(1)
            )
            if item is None:
                break
            item.state = ItemState.PROCESSING
            item.attempts += 1
            item.error = None
            item_id = item.id
            spec = IntakeSpec.model_validate(item.spec)
        try:
            manifest = artifacts.capture(spec, root)
        except TraceProofError as exc:
            with store.transaction() as session:
                item = session.get(ImportItem, item_id)
                item.state, item.error = ItemState.FAILED, str(exc)
                session.get(Run, item.run_id).state = RunState.FAILED
            continue
        with store.transaction() as session:
            if session.get(Snapshot, manifest.snapshot_id) is None:
                session.add(
                    Snapshot(
                        id=manifest.snapshot_id,
                        repo_id=spec.repo_id,
                        manifest=manifest.model_dump(mode="json"),
                    )
                )
                session.flush()
            item = session.get(ImportItem, item_id)
            run = session.get(Run, item.run_id)
            run.snapshot_id, run.state = manifest.snapshot_id, RunState.SNAPSHOTTED
            item.state = ItemState.SNAPSHOTTED
    return import_status(store, import_id)


def render_json(value: dict) -> str:
    return json.dumps(value, indent=2)
