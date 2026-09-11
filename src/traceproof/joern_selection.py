"""Deterministic, sequential discovery selection; inventory is not coverage."""

from pathlib import Path

from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.languages import EXTENSIONS

PROFILES = {
    "python": (
        "python-flask-system-v1",
        "python-flask-path-v1",
        "python-flask-ssrf-v1",
        "python-flask-sql-v1",
    ),
    "java": (None, "java-spring-file-path-v1", "java-spring-url-stream-v1"),
    "csharp": (None,),
    "javascript": ("express-request-eval-v1",),
    "typescript": ("express-request-eval-v1",),
    "go": ("go-http-shell-v1",),
    "rust": ("rust-env-shell-v1",),
    "c": ("c-family-argv-system-v1",),
    "cpp": ("c-family-argv-system-v1",),
}
EXTENSIONS = {**EXTENSIONS, ".c": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp"}


def selection(manifest, requested="auto"):
    detected = sorted(
        {
            EXTENSIONS[Path(f.path).suffix.lower()]
            for f in manifest.files
            if Path(f.path).suffix.lower() in EXTENSIONS
        }
    )
    languages = detected if requested == "auto" else [requested]
    if not languages:
        raise TraceProofError(
            "No recognized source language; select --language explicitly for header-only C"
        )
    return detected, [
        (language, profile) for language in languages for profile in PROFILES.get(language, (None,))
    ]


def scan_selected(
    store,
    run_id,
    language,
    joern_home,
    repair_dir,
    rust_home,
    extraction_timeout,
    query_timeout,
    skip_existing=False,
    *,
    advisory=None,
):
    from traceproof.joern_pipeline import scan_run

    if advisory is not None:
        raise TraceProofError(
            "Automatic profile selection is discovery-only; "
            "select an explicit --joern-profile for advisory"
        )
    run, manifest, _ = verified_source(store, run_id)
    detected, plan = selection(manifest, language)
    items = []
    for selected, profile in plan:
        item = {"language": selected, "discovery_profile": profile or "default"}
        if selected not in PROFILES:
            items.append({**item, "status": "unsupported_language", "report_id": None})
            continue
        try:
            result = scan_run(
                store,
                run_id,
                selected,
                joern_home,
                repair_dir,
                rust_home,
                extraction_timeout,
                query_timeout,
                skip_existing,
                profile,
            )
        except TraceProofError as exc:
            result = {"status": "scope_error", "error": str(exc), "report_id": None}
        items.append({**result, **item})
    return {
        "schema_version": "1",
        "engine": "joern",
        "repo_id": run.repo_id,
        "run_id": run_id,
        "requested_language": language,
        "selection_policy": "all-bounded-profiles-v1",
        "detected_languages": detected,
        "items": items,
        "report_id": None,
        "report_ids": [item["report_id"] for item in items if item.get("report_id")],
        "status": "incomplete",
        "model_calls": 0,
        "security_completion_verified": False,
        "scope": (
            "Separate per-language/profile reports; no cross-language flow or clean verdict. "
            "Unknown file extensions are not detected; "
            "profile extraction limitations remain applicable."
        ),
    }
