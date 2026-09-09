"""Resumable indexing with atomic publication and read-only report retrieval."""

import hashlib
import json
import subprocess
import sys
from collections import Counter
from uuid import uuid4

from sqlalchemy import select

from traceproof.artifacts import ArtifactStore
from traceproof.domain import TraceProofError
from traceproof.persistence import IndexedFile, Run, Snapshot, SourceIndex
from traceproof.python_parser import MAX_BYTES

VERSION = (
    f"python-ast-v1-py{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
)


def snapshot_for_run(store, run_id):
    with store.transaction() as session:
        run = session.get(Run, run_id)
        if run is None or run.snapshot_id is None:
            raise TraceProofError("Run has no captured snapshot")
        snapshot = session.get(Snapshot, run.snapshot_id)
        return run, snapshot


def verified_source(store, run_id):
    run, snapshot = snapshot_for_run(store, run_id)
    artifacts = ArtifactStore(store.root)
    manifest = artifacts.verify(snapshot.id)
    if manifest.model_dump(mode="json") != snapshot.manifest:
        raise TraceProofError("Snapshot manifest differs from its admitted database record")
    return run, manifest, artifacts.path(snapshot.id) / "tree"


def parse_isolated(source):
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-m", "traceproof.python_parser"],
            input=source,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode:
            return {"status": "parser_failed", "symbols": [], "calls": []}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "symbols": [], "calls": []}


def build_index(store, run_id):
    """Caller holds exclusive_worker. Completed file checkpoints survive process death."""
    run, manifest, tree = verified_source(store, run_id)
    with store.transaction() as session:
        index = session.scalar(
            select(SourceIndex).where(
                SourceIndex.snapshot_id == manifest.snapshot_id, SourceIndex.version == VERSION
            )
        )
        if index is None:
            index = SourceIndex(
                id=str(uuid4()), snapshot_id=manifest.snapshot_id, version=VERSION, state="building"
            )
            session.add(index)
        index_id = index.id
        published = index.state == "published"
    if published:
        return coverage_report(store, run_id)
    with store.transaction() as session:
        done = set(
            session.scalars(select(IndexedFile.path).where(IndexedFile.index_id == index_id))
        )
    for record in sorted(manifest.files, key=lambda file: file.path):
        if record.path in done:
            continue
        result = {"status": "not_supported", "symbols": [], "calls": []}
        if record.path.endswith(".py"):
            if record.size_bytes > MAX_BYTES:
                result["status"] = "size_limit"
            else:
                source = (tree / record.path).read_bytes()
                if hashlib.sha256(source).hexdigest() != record.sha256:
                    raise TraceProofError("Source changed during indexing")
                result = parse_isolated(source)
        result.update(path=record.path, sha256=record.sha256, size_bytes=record.size_bytes)
        with store.transaction() as session:
            session.add(
                IndexedFile(id=str(uuid4()), index_id=index_id, path=record.path, result=result)
            )
    # Detect concurrent local modification before making any index queryable.
    verified_source(store, run_id)
    with store.transaction() as session:
        results = session.scalars(
            select(IndexedFile.result)
            .where(IndexedFile.index_id == index_id)
            .order_by(IndexedFile.path)
        ).yield_per(1)
        counts, file_coverage = Counter(), []
        python_files = functions = calls = 0
        for item in results:
            counts[item["status"]] += 1
            python_files += item["path"].endswith(".py")
            functions += sum(symbol["kind"] == "function" for symbol in item["symbols"])
            calls += len(item["calls"])
            file_coverage.append(
                {key: item[key] for key in ("path", "sha256", "size_bytes", "status")}
            )
        gate = (
            "ready"
            if python_files and counts["parsed"] == python_files and functions
            else "blocked"
        )
        index = session.get(SourceIndex, index_id)
        index.report = {
            "schema_version": "1",
            "report_kind": "index_coverage",
            "index_id": index_id,
            "index_version": VERSION,
            "snapshot_id": manifest.snapshot_id,
            "classification": manifest.classification,
            "security_analysis_performed": False,
            "security_verdict": "not_assessed",
            "finding_count": None,
            "python_index_gate": gate,
            "total_files": len(file_coverage),
            "python_files": python_files,
            "parsed_python_files": counts["parsed"],
            "python_parse_fraction": counts["parsed"] / python_files if python_files else None,
            "function_count": functions,
            "call_count": calls,
            "unresolved_call_count": calls,
            "files": file_coverage,
            "limitations": [
                "Only .py files are indexed; other files are explicitly not supported.",
                "Calls are unresolved syntax; no interprocedural or taint reachability proof.",
                "The gate checks Python parsing and nonempty function inventory only.",
                "No security queries, LLM analysis, or benchmark evaluation have run.",
            ],
        }
        index.state = "published"
    return coverage_report(store, run_id)


def published_index(session, snapshot_id):
    index = session.scalar(
        select(SourceIndex).where(
            SourceIndex.snapshot_id == snapshot_id,
            SourceIndex.version == VERSION,
            SourceIndex.state == "published",
        )
    )
    if index is None:
        raise TraceProofError("No published index for this snapshot and parser version")
    return index


def coverage_report(store, run_id):
    run, snapshot = snapshot_for_run(store, run_id)
    with store.transaction() as session:
        index = published_index(session, snapshot.id)
        return {**index.report, "run_id": run.id, "repo_id": run.repo_id}


def repository_report(store, repo_id, run_id=None):
    with store.transaction() as session:
        query = select(Run).where(Run.repo_id == repo_id)
        if run_id:
            query = query.where(Run.id == run_id)
        run = session.scalar(query.order_by(Run.created_at.desc(), Run.id.desc()).limit(1))
        if run is None:
            raise TraceProofError("Repository/run not found")
        selected = run.id
    # Latest admitted run is intentional: never silently return an older successful run.
    return coverage_report(store, selected)


def query_index(store, run_id, kind="symbols", path=None, offset=0, limit=100):
    if kind not in {"symbols", "calls"} or not 1 <= limit <= 1000 or offset < 0:
        raise TraceProofError("Invalid index query")
    run, snapshot = snapshot_for_run(store, run_id)
    with store.transaction() as session:
        index = published_index(session, snapshot.id)
        query = select(IndexedFile).where(IndexedFile.index_id == index.id)
        if path is not None:
            query = query.where(IndexedFile.path == path)
        items, total = [], 0
        for file in session.scalars(query.order_by(IndexedFile.path)).yield_per(10):
            for entry in file.result[kind]:
                if offset <= total < offset + limit:
                    items.append(
                        {
                            **entry,
                            "evidence": {
                                "snapshot_id": snapshot.id,
                                "path": file.path,
                                "sha256": file.result["sha256"],
                                "line": entry["line"],
                                "end_line": entry["end_line"],
                            },
                        }
                    )
                total += 1
    return {
        "schema_version": "1",
        "run_id": run.id,
        "kind": kind,
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


def report_markdown(report):
    # JSON string quoting keeps metadata single-line; no raw source is included.
    return "\n".join(
        [
            "# TraceProof index coverage report",
            "",
            f"Repository: `{report['repo_id']}`",
            f"Run: `{report['run_id']}`",
            f"Snapshot: `{report['snapshot_id']}`",
            "",
            "**Security verdict: NOT ASSESSED. This is not a vulnerability scan report.**",
            "",
            f"Python index gate: **{report['python_index_gate']}**",
            f"Python files parsed: {report['parsed_python_files']} / {report['python_files']}",
            f"Functions: {report['function_count']}; "
            f"unresolved calls: {report['unresolved_call_count']}",
            "",
            "Limitations:",
            "",
            *[f"- {item}" for item in report["limitations"]],
            "",
            "Per-file coverage is available in the JSON report for dashboard ingestion.",
            "",
        ]
    )
