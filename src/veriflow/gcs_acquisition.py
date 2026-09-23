"""Generation-pinned archive handoff contract; network adapter is intentionally separate."""

import csv
import hashlib
import json
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from veriflow.domain import IntakeSpec, VeriFlowError


@dataclass(frozen=True)
class ObjectVersion:
    bucket: str
    name: str
    generation: str
    size: int


class ArchiveReader(Protocol):
    def stat(self, bucket: str, name: str, generation: str) -> ObjectVersion: ...

    def chunks(self, version: ObjectVersion) -> Iterable[bytes]: ...


def acquire_archive(
    reader,
    *,
    bucket,
    name,
    generation,
    expected_sha256,
    allowed_buckets,
    output,
    repo_id,
    owner,
    classification,
    max_bytes=100 * 1024 * 1024,
    timeout=300,
):
    """Reader must enforce generation and I/O deadlines; this adds stream/accounting gates."""
    if (
        bucket not in allowed_buckets
        or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket)
        or not isinstance(name, str)
        or not name
        or len(name.encode()) > 1024
        or any(ord(c) < 32 or ord(c) == 127 for c in name)
        or not re.fullmatch(r"[1-9][0-9]{0,29}", generation)
        or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256)
        or not 1 <= max_bytes <= 1024 * 1024 * 1024
        or not 1 <= timeout <= 900
    ):
        raise VeriFlowError(
            "Require approved bucket, object, generation, SHA-256 and bounded limits"
        )
    suffix = next(
        (suffix for suffix in (".tar.gz", ".tgz", ".tar", ".zip") if name.endswith(suffix)), None
    )
    if suffix is None:
        raise VeriFlowError("GCS object must name a supported TAR/ZIP archive")
    output = Path(output).absolute()
    try:
        spec = IntakeSpec(
            repo_id=repo_id,
            source_type="pvc",
            source_uri=str(output / ("source" + suffix)),
            owner=owner,
            classification=classification,
            sha256=expected_sha256,
        )
    except ValidationError:
        raise VeriFlowError("Invalid acquisition metadata") from None
    try:
        output.mkdir(mode=0o700)
    except FileExistsError:
        raise VeriFlowError("Acquisition output already exists") from None
    receipt = dict(
        schema_version="1",
        kind="gcs",
        repo_id=repo_id,
        state="failed",
        bucket=bucket,
        object=name,
        generation=generation,
        model_calls=0,
        scans_started=0,
        provenance_binding="archive_digest_only",
    )
    archive = Path(spec.source_uri)
    deadline = time.monotonic() + timeout
    try:
        version = reader.stat(bucket, name, generation)
        if (version.bucket, version.name, version.generation) != (bucket, name, generation):
            raise VeriFlowError("GCS object version mismatch")
        if not 0 < version.size <= max_bytes:
            raise VeriFlowError("GCS object exceeds size limit or is empty")
        digest, total = hashlib.sha256(), 0
        with archive.open("xb") as target:
            for chunk in reader.chunks(version):
                if not isinstance(chunk, bytes) or not chunk or len(chunk) > 1024 * 1024:
                    raise VeriFlowError("Invalid or oversized archive stream chunk")
                total += len(chunk)
                if total > version.size or time.monotonic() > deadline:
                    raise VeriFlowError("GCS acquisition exceeded size or time limit")
                target.write(chunk)
                digest.update(chunk)
        if (
            time.monotonic() > deadline
            or total != version.size
            or digest.hexdigest() != expected_sha256
        ):
            raise VeriFlowError("GCS archive size, digest or deadline mismatch")
        receipt.update(
            state="acquired",
            archive_sha256=digest.hexdigest(),
            size=total,
            limitations=[
                "Archive contents must pass offline intake validation",
                "Supplied cloud metadata; remote object history is not authenticated",
            ],
        )
        with (output / "archives.csv").open("x", newline="") as target:
            row = spec.model_dump(
                exclude={"acquisition_data", "acquisition_receipt", "acquisition_sha256"}
            )
            row.update(
                acquisition_receipt=str(output / "acquisition.json"),
                acquisition_sha256=hashlib.sha256(
                    json.dumps(receipt, indent=2).encode()
                ).hexdigest(),
            )
            writer = csv.DictWriter(target, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        return receipt
    except Exception as exc:
        archive.unlink(missing_ok=True)
        (output / "archives.csv").unlink(missing_ok=True)
        receipt["error_type"] = type(exc).__name__
        if isinstance(exc, VeriFlowError):
            raise
        raise VeriFlowError("GCS acquisition failed; no scan input published") from None
    finally:
        (output / "acquisition.json").write_text(json.dumps(receipt, indent=2))
