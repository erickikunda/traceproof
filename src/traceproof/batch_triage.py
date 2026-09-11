"""Sequential, explicitly requested candidate triage using existing budget/evidence gates."""

import hashlib

from sqlalchemy import func, select

from traceproof.bundles import build_bundle, canonical
from traceproof.domain import TraceProofError
from traceproof.history import validate_page
from traceproof.persistence import Candidate, Run, ScanAttempt, TriageBudget
from traceproof.triage import triage

CONTINUE_STATES = {"completed", "evidence_rejected", "unsupported_rule", "incomplete_evidence"}


def triage_attempt(
    store, repo_id, attempt_id, config, adapter, key, offset=0, limit=1, *, review_policy=None
):
    if review_policy is not None:
        from traceproof.joern_claims import require_policy

        require_policy(review_policy)
    validate_page(offset, limit)
    if limit > 100:
        raise TraceProofError("Batch triage limit must not exceed 100 candidates")
    if not key.strip() or len(key) > 200:
        raise TraceProofError("Batch key must contain 1–200 characters")
    with store.transaction() as session:
        attempt = session.scalar(
            select(ScanAttempt)
            .join(Run)
            .where(ScanAttempt.id == attempt_id, Run.repo_id == repo_id)
        )
        if attempt is None:
            raise TraceProofError("Analysis attempt does not belong to repository")
        if attempt.report.get("status") not in {"completed", "partial"}:
            raise TraceProofError("Batch triage requires a completed or partial query attempt")
        if session.get(TriageBudget, attempt.run_id) is None:
            raise TraceProofError("Configure a run triage budget before requesting triage")
        run_id = attempt.run_id
        scope = Candidate.attempt_id == attempt_id
        total = session.scalar(select(func.count()).select_from(Candidate).where(scope))
        fingerprints = list(
            session.scalars(
                select(Candidate.fingerprint)
                .where(scope)
                .order_by(Candidate.fingerprint)
                .offset(offset)
                .limit(limit)
            )
        )
    rows = []
    halted = False
    next_offset = offset
    for fingerprint in fingerprints:
        identity = [key, attempt_id, fingerprint]
        if review_policy is not None:
            identity.append(review_policy)
        request_key = "batch:" + hashlib.sha256(canonical(identity)).hexdigest()
        row = {"candidate_fingerprint": fingerprint, "request_key": request_key}
        try:
            bundle = build_bundle(store, attempt_id, fingerprint)
            result = triage(
                store,
                bundle["bundle_id"],
                config,
                adapter,
                request_key,
                **({"review_policy": review_policy} if review_policy else {}),
            )
        except TraceProofError as exc:
            rows.append({**row, "state": "operation_error", "error": str(exc)})
            halted = True
            break
        rows.append(
            {
                **row,
                **{
                    field: result.get(field)
                    for field in (
                        "triage_id",
                        "bundle_id",
                        "state",
                        "disposition",
                        "accounted_micro_usd",
                    )
                },
            }
        )
        next_offset += 1
        if result["state"] not in CONTINUE_STATES:
            halted = True
            break
    return {
        "schema_version": "1",
        "repo_id": repo_id,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "status": "halted" if halted else "page_complete",
        "offset": offset,
        "limit": limit,
        "total_candidates": total,
        "selected_candidates": len(fingerprints),
        "items": rows,
        "next_offset": next_offset if next_offset < total else None,
        "scope": "Advisory triage only; outcomes do not confirm or suppress vulnerabilities",
    }
