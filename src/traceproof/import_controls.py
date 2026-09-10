"""Durable cooperative import dispatch controls; running work is never killed."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from traceproof.domain import TraceProofError
from traceproof.history import validate_page
from traceproof.persistence import ImportBatch, ImportControl


def current_control(session, import_id):
    if session.get(ImportBatch, import_id) is None:
        raise TraceProofError("Import not found")
    record = session.scalar(
        select(ImportControl)
        .where(ImportControl.import_id == import_id)
        .order_by(ImportControl.revision.desc())
        .limit(1)
    )
    return {
        "state": record.state if record else "active",
        "revision": record.revision if record else 0,
    }


def control_status(store, import_id, offset=0, limit=100):
    validate_page(offset, limit)
    with store.transaction() as session:
        current = current_control(session, import_id)
        records = session.scalars(
            select(ImportControl)
            .where(ImportControl.import_id == import_id)
            .order_by(ImportControl.revision.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = [
            {
                key: getattr(record, key)
                for key in ("revision", "state", "request_key", "reason", "created_at")
            }
            for record in records
        ]
        return {
            "schema_version": "1",
            "import_id": import_id,
            **current,
            "history": rows,
            "offset": offset,
            "limit": limit,
            "next_offset": offset + len(rows) if offset + len(rows) < current["revision"] else None,
        }


def set_control(store, import_id, state, key, reason, expected_revision):
    if state not in {"active", "paused", "cancelled"}:
        raise TraceProofError("Import dispatch state must be active, paused or cancelled")
    if not key.strip() or len(key) > 200 or not reason.strip() or len(reason) > 1000:
        raise TraceProofError("Provide a 1–200 character key and a 1–1000 character reason")
    if type(expected_revision) is not int or expected_revision < 0:
        raise TraceProofError("Expected revision must be a nonnegative integer")
    try:
        with store.transaction() as session:
            current = current_control(session, import_id)
            existing = session.scalar(
                select(ImportControl).where(
                    ImportControl.import_id == import_id, ImportControl.request_key == key
                )
            )
            if existing:
                if (existing.state, existing.reason, existing.revision - 1) != (
                    state,
                    reason,
                    expected_revision,
                ):
                    raise TraceProofError("Import control key was used for a different request")
                applied_revision = existing.revision
            else:
                if current["state"] == "cancelled":
                    raise TraceProofError("Import dispatch is cancelled and cannot be resumed")
                if current["revision"] != expected_revision:
                    raise TraceProofError(
                        "Import control revision changed; inspect import-control-status"
                    )
                if current["state"] == state:
                    raise TraceProofError("Import already has the requested dispatch state")
                applied_revision = current["revision"] + 1
                session.add(
                    ImportControl(
                        import_id=import_id,
                        revision=applied_revision,
                        state=state,
                        request_key=key,
                        reason=reason,
                        created_at=datetime.now(UTC).isoformat(),
                    )
                )
        return {
            "import_id": import_id,
            "applied_revision": applied_revision,
            "requested_state": state,
            "current": control_status(store, import_id),
        }
    except IntegrityError:
        raise TraceProofError("Concurrent control change; inspect status before retrying") from None
