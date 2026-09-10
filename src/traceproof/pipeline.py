"""Explicit local source-only orchestration; no automatic model calls or retries."""

from sqlalchemy import func, select

from traceproof.codeql import extract
from traceproof.codeql_resources import resource_settings
from traceproof.csharp_dependencies import load_profile
from traceproof.domain import TraceProofError
from traceproof.indexing import build_index, verified_source
from traceproof.java_dependencies import load_java_profile
from traceproof.java_index import build_java_index
from traceproof.languages import (
    adapter_for,
    select_language,
    validate_extraction_scope,
    validate_selection,
)
from traceproof.network_isolation import MODE, validate_offline
from traceproof.persistence import Run, ScanAttempt, exclusive_worker
from traceproof.reports import publish_report
from traceproof.scanning import analyze, query_entry


def scan_run(
    store,
    run_id,
    queries,
    extraction_timeout=300,
    query_timeout=600,
    *,
    skip_existing=False,
    threads=2,
    ram_mb=2048,
    language="python",
    java_profile="dependency-free",
    java_dependency_profile=None,
    allow_csharp_downloads=False,
    csharp_dependency_profile=None,
    csharp_offline=False,
):
    resources = resource_settings(threads, ram_mb)
    validate_selection(language, java_profile)
    requested_language = language
    if not 1 <= extraction_timeout <= 3600 or not 1 <= query_timeout <= 3600:
        raise TraceProofError("Stage timeouts must be between 1 and 3600 seconds")
    store.require_initialized()
    query = query_entry(store, queries)
    with exclusive_worker(store.root):
        if language == "auto":
            _, manifest, _ = verified_source(store, run_id)
            language = select_language(manifest, language)
            validate_selection(language, java_profile)
        validate_offline(
            language, csharp_dependency_profile, allow_csharp_downloads, csharp_offline
        )
        if java_dependency_profile is not None and language != "java":
            raise TraceProofError("Java dependency profiles require java")
        java_dependency_id = (
            load_java_profile(java_dependency_profile)["id"] if java_dependency_profile else ""
        )
        dependency_id = None
        if csharp_dependency_profile is not None:
            if language != "csharp":
                raise TraceProofError("C# dependency profiles require csharp")
            dependency_id = load_profile(csharp_dependency_profile)["id"]
        with store.transaction() as session:
            run = session.get(Run, run_id)
            if run is None:
                raise TraceProofError("Run not found")
            repo_id = run.repo_id
            if skip_existing:
                previous = session.scalar(
                    select(ScanAttempt)
                    .where(
                        ScanAttempt.run_id == run_id,
                        func.coalesce(
                            ScanAttempt.report["language_scope"]["java_dependency_profile"][
                                "id"
                            ].as_string(),
                            "",
                        )
                        == java_dependency_id,
                        func.coalesce(
                            ScanAttempt.report["language_scope"]["network_isolation"].as_string(),
                            "none",
                        )
                        == (MODE if csharp_offline else "none"),
                        func.coalesce(
                            ScanAttempt.report["language_scope"]["dependency_profile"][
                                "id"
                            ].as_string(),
                            "",
                        )
                        == (dependency_id or ""),
                        func.coalesce(ScanAttempt.report["language"].as_string(), "python")
                        == language,
                        func.coalesce(
                            ScanAttempt.report["language_scope"]["adapter_profile"].as_string(),
                            adapter_for(language).profile,
                        )
                        == (
                            f"java-{java_profile}-v1"
                            if language == "java"
                            else adapter_for(language).profile
                        ),
                    )
                    .order_by(ScanAttempt.created_at.desc(), ScanAttempt.id.desc())
                    .limit(1)
                )
                if previous is not None:
                    return {
                        "schema_version": "1",
                        "language": language,
                        "requested_language": requested_language,
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
            "language": language,
            "requested_language": requested_language,
        }
        if language == "python":
            index = build_index(store, run_id)
            result["python_index_gate"] = index["python_index_gate"]
            if index["python_index_gate"] != "ready":
                return {**result, "reason": "Python index is not ready; inspect repo-report"}
        else:
            _, manifest, _ = verified_source(store, run_id)
            result["language_scope"] = validate_extraction_scope(manifest, language, java_profile)
            if language == "java":
                result["java_syntax_index"] = build_java_index(store, run_id)
                if result["java_syntax_index"]["syntax_gate"] != "ready":
                    return {**result, "reason": "Java syntax index is blocked"}
        extraction = extract(
            store,
            run_id,
            timeout=extraction_timeout,
            language=requested_language,
            java_profile=java_profile,
            java_dependency_profile=java_dependency_profile,
            allow_csharp_downloads=allow_csharp_downloads,
            csharp_dependency_profile=csharp_dependency_profile,
            csharp_offline=csharp_offline,
            **resources,
        )
        result.update(
            extraction_id=extraction["attempt_id"],
            stopped_after="extraction",
            extraction_status=extraction["status"],
        )
        if extraction["status"] != "extracted":
            return {**result, "reason": "Extraction did not succeed; inspect codeql-status"}
        scan = analyze(store, extraction["attempt_id"], query, timeout=query_timeout, **resources)
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
