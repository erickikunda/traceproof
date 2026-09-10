"""Explicit local source-only orchestration; no automatic model calls or retries."""

from sqlalchemy import select

from traceproof.codeql import extract
from traceproof.domain import TraceProofError
from traceproof.indexing import build_index
from traceproof.persistence import Run, ScanAttempt, exclusive_worker
from traceproof.reports import publish_report
from traceproof.scanning import analyze, query_entry


def scan_run(
    store, run_id, queries, extraction_timeout=300, query_timeout=600, *, skip_existing=False
):
    if not 1 <= extraction_timeout <= 3600 or not 1 <= query_timeout <= 3600:
        raise TraceProofError("Stage timeouts must be between 1 and 3600 seconds")
    store.require_initialized()
    query = query_entry(store, queries)
    with exclusive_worker(store.root):
        with store.transaction() as session:
            run = session.get(Run, run_id)
            if run is None:
                raise TraceProofError("Run not found")
            repo_id = run.repo_id
            if skip_existing:
                previous = session.scalar(
                    select(ScanAttempt)
                    .where(ScanAttempt.run_id == run_id)
                    .order_by(ScanAttempt.created_at.desc(), ScanAttempt.id.desc())
                    .limit(1)
                )
                if previous is not None:
                    return {
                        "schema_version": "1",
                        "repo_id": repo_id,
                        "run_id": run_id,
                        "status": "skipped_existing_attempt",
                        "attempt_id": previous.id,
                        "analysis_status": previous.report.get("status", "unknown"),
                        "report_id": None,
                        "model_calls": 0,
                        "reason": "Existing attempt retained; use explicit rescan to run again",
                    }
        result = {
            "schema_version": "1",
            "repo_id": repo_id,
            "run_id": run_id,
            "status": "blocked",
            "stopped_after": "index",
            "extraction_id": None,
            "attempt_id": None,
            "report_id": None,
            "model_calls": 0,
            "security_completion_verified": False,
        }
        index = build_index(store, run_id)
        result["python_index_gate"] = index["python_index_gate"]
        if index["python_index_gate"] != "ready":
            return {**result, "reason": "Python index is not ready; inspect repo-report"}
        extraction = extract(store, run_id, timeout=extraction_timeout)
        result.update(
            extraction_id=extraction["attempt_id"],
            stopped_after="extraction",
            extraction_status=extraction["status"],
        )
        if extraction["status"] != "extracted":
            return {**result, "reason": "Extraction did not succeed; inspect codeql-status"}
        scan = analyze(store, extraction["attempt_id"], query, timeout=query_timeout)
        result.update(attempt_id=scan["attempt_id"], analysis_status=scan["status"])
    # Publication owns its own lock. Pin the attempt even if other work starts between stages.
    report = publish_report(store, repo_id, run_id, scan["attempt_id"])
    ready = report["static_review_readiness"]["state"] == "ready_for_review"
    return {
        **result,
        "status": "ready_for_review" if ready else "incomplete",
        "stopped_after": "publication",
        "report_id": report["report_id"],
        "candidate_count": report["candidate_count"],
        "reason": "Static review readiness only; not a clean security verdict",
    }
