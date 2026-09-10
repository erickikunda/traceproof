"""Exact-attempt, bounded retrieval of original integrity-checked SARIF bytes."""

import hashlib
import os
import stat
from pathlib import Path

from sqlalchemy import select

from traceproof.domain import TraceProofError
from traceproof.persistence import Run, ScanAttempt
from traceproof.sarif import MAX_SARIF_BYTES


def get_sarif(store, repo_id, attempt_id):
    with store.transaction() as session:
        attempt = session.scalar(
            select(ScanAttempt)
            .join(Run)
            .where(ScanAttempt.id == attempt_id, Run.repo_id == repo_id)
        )
        if attempt is None:
            raise TraceProofError("Analysis attempt does not belong to repository")
        report = attempt.report
        digest = report.get("sarif_sha256")
        if report.get("status") not in {"completed", "partial"} or not digest:
            raise TraceProofError("No integrity-recorded SARIF for this attempt")
    if Path(attempt_id).name != attempt_id or attempt_id in {".", ".."}:
        raise TraceProofError("Invalid artifact identity")
    # Never follow a path supplied in stored tool output or SARIF itself.
    path = store.root / "scans" / attempt_id / "results.sarif"
    try:
        if path.resolve(strict=True) != path:
            raise TraceProofError("SARIF artifact links are not supported")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SARIF_BYTES:
                raise TraceProofError("SARIF artifact is not a bounded regular file")
            raw = handle.read(MAX_SARIF_BYTES + 1)
    except OSError:
        raise TraceProofError(
            "SARIF artifact unavailable; check local retention and storage"
        ) from None
    if len(raw) > MAX_SARIF_BYTES or hashlib.sha256(raw).hexdigest() != digest:
        raise TraceProofError("SARIF artifact integrity check failed")
    return raw
