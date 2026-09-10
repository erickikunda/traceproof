"""Bounded sequential scans of admitted import rows; no background scheduling."""

from collections import Counter

from traceproof.domain import TraceProofError
from traceproof.history import validate_page
from traceproof.intake import import_status
from traceproof.pipeline import scan_run
from traceproof.scanning import query_entry


def scan_import(
    store,
    import_id,
    query,
    offset=0,
    limit=1,
    rescan=False,
    extraction_timeout=300,
    query_timeout=600,
):
    validate_page(offset, limit)
    if not 1 <= extraction_timeout <= 3600 or not 1 <= query_timeout <= 3600:
        raise TraceProofError("Stage timeouts must be between 1 and 3600 seconds")
    query = query_entry(store, query)
    admitted = import_status(store, import_id)["items"]
    selected = admitted[offset : offset + limit]
    results = []
    for item in selected:
        row = {
            "item_id": item["item_id"],
            "row_number": item["row_number"],
            "run_id": item["run_id"],
            "intake_state": item["state"],
        }
        if item["state"] != "snapshotted" or not item["run_id"]:
            results.append({**row, "status": "skipped_intake_not_ready", "report_id": None})
            continue
        try:
            result = scan_run(
                store,
                item["run_id"],
                query,
                extraction_timeout,
                query_timeout,
                skip_existing=not rescan,
            )
        except TraceProofError as exc:
            # Expected row failures remain explicit; infrastructure errors stop the command.
            result = {"status": "row_error", "error": str(exc), "report_id": None}
        results.append({**row, **result})
    return {
        "schema_version": "1",
        "import_id": import_id,
        "offset": offset,
        "limit": limit,
        "total_rows": len(admitted),
        "selected_rows": len(selected),
        "next_offset": offset + len(selected) if offset + len(selected) < len(admitted) else None,
        "rescan_requested": rescan,
        "counts": dict(Counter(row["status"] for row in results)),
        "items": results,
        "model_calls": 0,
        "scope": "Sequential local source-only work; skipped/failed rows are not clean scans",
    }
