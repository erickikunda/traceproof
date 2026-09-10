"""Read-only discovery of admitted runs and analysis attempts, including unpublished work."""

from sqlalchemy import func, select

from traceproof.domain import TraceProofError
from traceproof.persistence import Repository, Run, ScanAttempt


def validate_page(offset, limit):
    if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 1000:
        raise TraceProofError("Invalid history pagination")


def require_repository(session, repo_id):
    if session.get(Repository, repo_id) is None:
        raise TraceProofError("Repository not found")


def page(repo_id, offset, limit, total, rows):
    return {
        "schema_version": "1",
        "repo_id": repo_id,
        "offset": offset,
        "limit": limit,
        "total": total,
        "next_offset": offset + len(rows) if offset + len(rows) < total else None,
        "items": rows,
        "consistency": "One read transaction per page; new work may shift later offset pages",
    }


def run_history(store, repo_id, offset=0, limit=100):
    validate_page(offset, limit)
    with store.transaction() as session:
        require_repository(session, repo_id)
        total = session.scalar(select(func.count()).select_from(Run).where(Run.repo_id == repo_id))
        latest_id = (
            select(ScanAttempt.id)
            .where(ScanAttempt.run_id == Run.id)
            .order_by(ScanAttempt.created_at.desc(), ScanAttempt.id.desc())
            .limit(1)
            .correlate(Run)
            .scalar_subquery()
        )
        rows = session.execute(
            select(Run, latest_id.label("latest_attempt_id"))
            .where(Run.repo_id == repo_id)
            .order_by(Run.created_at.desc(), Run.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return page(
            repo_id,
            offset,
            limit,
            total,
            [
                {
                    "run_id": run.id,
                    "created_at": run.created_at,
                    "state": run.state,
                    "profile": run.profile,
                    "snapshot_id": run.snapshot_id,
                    "latest_attempt_id": attempt_id,
                }
                for run, attempt_id in rows
            ],
        )


def scan_history(store, repo_id, run_id=None, offset=0, limit=100):
    validate_page(offset, limit)
    with store.transaction() as session:
        require_repository(session, repo_id)
        if run_id is not None:
            run = session.get(Run, run_id)
            if run is None or run.repo_id != repo_id:
                raise TraceProofError("Run does not belong to repository")
        scope = [Run.repo_id == repo_id]
        if run_id is not None:
            scope.append(Run.id == run_id)
        total = session.scalar(
            select(func.count()).select_from(ScanAttempt).join(Run).where(*scope)
        )
        rows = session.scalars(
            select(ScanAttempt)
            .join(Run)
            .where(*scope)
            .order_by(
                Run.created_at.desc(),
                Run.id.desc(),
                ScanAttempt.created_at.desc(),
                ScanAttempt.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = page(
            repo_id,
            offset,
            limit,
            total,
            [
                {
                    "attempt_id": attempt.id,
                    "run_id": attempt.run_id,
                    "created_at": attempt.created_at,
                    "status": attempt.report.get("status", "unknown"),
                    "execution_complete": attempt.report.get("execution_complete"),
                    "candidate_count": attempt.report.get("candidate_count"),
                }
                for attempt in rows
            ],
        )
        return {
            **result,
            "run_id": run_id,
            "scope": "Stored query attempts; status/counts do not establish security completeness",
        }
