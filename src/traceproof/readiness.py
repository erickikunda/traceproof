"""Read-only readiness for reviewing Python static candidates, never a clean verdict."""

from sqlalchemy import select

from traceproof.indexing import VERSION
from traceproof.persistence import SourceIndex


def static_readiness(session, snapshot_id, scan):
    index = (
        session.scalar(
            select(SourceIndex).where(
                SourceIndex.snapshot_id == snapshot_id,
                SourceIndex.version == VERSION,
                SourceIndex.state == "published",
            )
        )
        if snapshot_id
        else None
    )
    coverage = index.report if index and index.report else {}
    reasons = []
    if not coverage:
        reasons.append("current_python_index_missing")
    elif coverage.get("python_index_gate") != "ready":
        reasons.append("python_index_blocked")
    if scan.get("status") != "completed" or scan.get("execution_complete") is not True:
        reasons.append("static_analysis_incomplete")
    if scan.get("diagnostic_errors") != 0:
        reasons.append("analysis_errors_or_unknown_diagnostics")
    if scan.get("unmapped_candidates") != 0:
        reasons.append("unmapped_candidates_or_unknown_locations")
    if scan.get("candidate_count") is None:
        reasons.append("candidate_count_unknown")
    return {
        "version": "1",
        "state": "incomplete" if reasons else "ready_for_review",
        "reasons": reasons,
        "index_id": index.id if index else None,
        "index_version": index.version if index else None,
        "python_index_gate": coverage.get("python_index_gate", "unknown"),
        "python_files": coverage.get("python_files"),
        "parsed_python_files": coverage.get("parsed_python_files"),
        "total_files": coverage.get("total_files"),
        "scope": "Python parsing and recorded static execution only",
        "security_completion_verified": False,
    }
