"""Bounded discovery of local import batches without exposing intake paths or keys."""

from sqlalchemy import func, select

from traceproof.domain import TraceProofError
from traceproof.history import validate_page
from traceproof.persistence import ImportBatch, ImportControl, ImportItem


def import_history(store, state=None, offset=0, limit=100):
    validate_page(offset, limit)
    if state not in {None, "active", "paused", "cancelled"}:
        raise TraceProofError("Dispatch state must be active, paused or cancelled")
    latest = (
        select(ImportControl.revision)
        .where(ImportControl.import_id == ImportBatch.id)
        .order_by(ImportControl.revision.desc())
        .limit(1)
        .correlate(ImportBatch)
        .scalar_subquery()
    )
    dispatch = func.coalesce(ImportControl.state, "active")
    query = select(
        ImportBatch.id,
        ImportBatch.created_at,
        ImportBatch.request_sha256,
        dispatch.label("dispatch_state"),
        func.coalesce(ImportControl.revision, 0).label("control_revision"),
    ).outerjoin(
        ImportControl,
        (ImportControl.import_id == ImportBatch.id) & (ImportControl.revision == latest),
    )
    if state is not None:
        query = query.where(dispatch == state)
    with store.transaction() as session:
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        batches = (
            session.execute(
                query.order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .mappings()
            .all()
        )
        ids = [batch["id"] for batch in batches]
        counts = {identity: {} for identity in ids}
        if ids:
            for import_id, intake_state, count in session.execute(
                select(ImportItem.import_id, ImportItem.state, func.count())
                .where(ImportItem.import_id.in_(ids))
                .group_by(ImportItem.import_id, ImportItem.state)
            ):
                counts[import_id][intake_state] = count
        return {
            "schema_version": "1",
            "state_filter": state,
            "offset": offset,
            "limit": limit,
            "total": total,
            "next_offset": offset + len(batches) if offset + len(batches) < total else None,
            "items": [
                {
                    "import_id": batch["id"],
                    "created_at": batch["created_at"],
                    "request_sha256": batch["request_sha256"],
                    "dispatch_state": batch["dispatch_state"],
                    "control_revision": batch["control_revision"],
                    "total_rows": sum(counts[batch["id"]].values()),
                    "intake_counts": counts[batch["id"]],
                }
                for batch in batches
            ],
            "consistency": "One read transaction per page; new work may shift later pages",
            "scope": "Import dispatch and intake counts only; no security completion implied",
        }
