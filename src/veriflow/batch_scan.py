"""Bounded sequential scans of admitted import rows; no background scheduling."""

from collections import Counter

from veriflow.codeql_resources import resource_settings
from veriflow.domain import TraceProofError
from veriflow.history import validate_page
from veriflow.import_controls import control_status
from veriflow.intake import import_status
from veriflow.languages import validate_selection
from veriflow.pipeline import scan_run
from veriflow.scanning import query_entry


def scan_import(
    store,
    import_id,
    query=None,
    offset=0,
    limit=1,
    rescan=False,
    extraction_timeout=300,
    query_timeout=600,
    *,
    threads=2,
    ram_mb=2048,
    language="python",
    java_profile="dependency-free",
    java_dependency_profile=None,
    allow_csharp_downloads=False,
    csharp_dependency_profile=None,
    csharp_offline=False,
    engine="codeql",
    joern_home=None,
    joern_repair_dir=None,
    rust_home=None,
    joern_profile=None,
    advisory=None,
):
    if advisory is not None and engine != "joern":
        raise TraceProofError("Scan advisory options require engine joern")
    resources = resource_settings(threads, ram_mb)
    if engine == "joern":
        from veriflow.joern_pipeline import validate_options

        validate_options(
            query,
            language,
            joern_home,
            threads,
            ram_mb,
            java_profile=java_profile,
            java_dependency_profile=java_dependency_profile,
            allow_csharp_downloads=allow_csharp_downloads,
            csharp_dependency_profile=csharp_dependency_profile,
            csharp_offline=csharp_offline,
        )
    elif engine == "codeql":
        if query is None or any(
            x is not None for x in (joern_home, joern_repair_dir, rust_home, joern_profile)
        ):
            raise TraceProofError("CodeQL requires queries and does not accept Joern tooling")
        validate_selection(language, java_profile)
    else:
        raise TraceProofError("Unsupported scanner engine")
    validate_page(offset, limit)
    if not 1 <= extraction_timeout <= 3600 or not 1 <= query_timeout <= 3600:
        raise TraceProofError("Stage timeouts must be between 1 and 3600 seconds")
    if engine == "codeql":
        query = query_entry(store, query)
    intake = import_status(store, import_id)
    admitted = intake["items"]
    selected = admitted[offset : offset + limit]
    results = []
    dispatch_state = intake["dispatch_control"]["state"]
    for item in selected:
        dispatch_state = control_status(store, import_id, limit=1)["state"]
        if dispatch_state != "active":
            break
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
                **resources,
                language=language,
                java_profile=java_profile,
                java_dependency_profile=java_dependency_profile,
                allow_csharp_downloads=allow_csharp_downloads,
                csharp_dependency_profile=csharp_dependency_profile,
                csharp_offline=csharp_offline,
                engine=engine,
                joern_home=joern_home,
                joern_repair_dir=joern_repair_dir,
                rust_home=rust_home,
                joern_profile=joern_profile,
                **({"advisory": advisory} if advisory is not None else {}),
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
        "next_offset": offset + len(results)
        if dispatch_state != "cancelled" and offset + len(results) < len(admitted)
        else None,
        "dispatch_status": dispatch_state if dispatch_state != "active" else "page_complete",
        "rescan_requested": rescan,
        "counts": dict(Counter(row["status"] for row in results)),
        "items": results,
        "model_calls": sum(row.get("model_calls", 0) for row in results),
        **(
            {"live_model_calls": sum(row.get("live_model_calls", 0) for row in results)}
            if advisory is not None
            else {}
        ),
        "scope": "Sequential bounded work; skipped/failed rows and advisories are not clean scans",
    }
