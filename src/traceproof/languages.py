"""Explicit language capabilities and snapshot inventory; detection is not coverage."""

from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath

from traceproof.domain import TraceProofError


@dataclass(frozen=True)
class LanguageAdapter:
    language: str
    extractor: str
    profile: str
    semantic_index: str
    evidence_gate: str


ADAPTERS = {
    "csharp": LanguageAdapter(
        "csharp", "csharp", "csharp-source-only-v1", "not_qualified", "aspnet_sql_review_v2"
    ),
    "python": LanguageAdapter(
        "python", "python", "python-source-v1", "python_ast", "python_claims"
    ),
    "java": LanguageAdapter(
        "java",
        "java",
        "java-dependency-free-v1",
        "not_qualified",
        "spring_requestparam_sql_review_v1",
    ),
}
EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".cs": "csharp",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".kt": "kotlin",
}


def adapter_for(language):
    if language not in ADAPTERS:
        raise TraceProofError("Implemented extraction languages are python, java and csharp")
    return ADAPTERS[language]


def select_language(manifest, requested):
    if requested != "auto":
        adapter_for(requested)
        return requested
    detected = sorted(
        {EXTENSIONS.get(PurePosixPath(file.path).suffix.lower()) for file in manifest.files}
        - {None}
    )
    if len(detected) != 1 or detected[0] not in ADAPTERS:
        names = ", ".join(detected) or "none"
        raise TraceProofError(
            f"Automatic selection requires one supported source language; detected: {names}. "
            "Choose an explicit language for partial coverage."
        )
    return detected[0]


def validate_selection(language, java_profile):
    if language == "auto":
        if java_profile not in {"dependency-free", "source-only"}:
            raise TraceProofError("Unknown Java profile")
    else:
        validate_profile(language, java_profile)


def language_scope(manifest, language):
    adapter = adapter_for(language)
    counts = Counter(
        EXTENSIONS.get(PurePosixPath(file.path).suffix.lower(), "unclassified")
        for file in manifest.files
    )
    return {
        "version": "1",
        "snapshot_id": manifest.snapshot_id,
        "selected_language": language,
        "adapter_profile": adapter.profile,
        "detected_file_counts": dict(sorted(counts.items())),
        "selected_file_count": counts[language],
        "unselected_languages": sorted(set(counts) - {language, "unclassified"}),
        "semantic_index": adapter.semantic_index,
        "evidence_gate": adapter.evidence_gate,
        "repository_security_completion_verified": False,
    }


def validate_profile(language, java_profile):
    adapter_for(language)
    if java_profile not in {"dependency-free", "source-only"} or (
        language != "java" and java_profile != "dependency-free"
    ):
        raise TraceProofError(
            "Java profile must be dependency-free or source-only; source-only requires java"
        )


def validate_extraction_scope(manifest, language, java_profile="dependency-free"):
    validate_profile(language, java_profile)
    scope = language_scope(manifest, language)
    if not scope["selected_file_count"]:
        raise TraceProofError("Snapshot contains no files for the selected language")
    if language == "csharp":
        scope.update(
            dependency_resolution="not_qualified",
            generated_code="not_qualified",
            build_execution="not_requested",
            framework_coverage="not_qualified",
            package_access="extractor_managed_not_qualified",
            razor_views="omitted",
            omitted_file_count=len(manifest.files) - scope["selected_file_count"],
            extraction_input="verified_csharp_only_copy",
        )
    if language == "java" and java_profile == "source-only":
        scope.update(
            adapter_profile="java-source-only-v1",
            dependency_resolution="not_qualified",
            generated_code="not_qualified",
            build_execution="not_requested",
            omitted_file_count=len(manifest.files) - scope["selected_file_count"],
            extraction_input="verified_java_only_copy",
        )
    if language == "java" and java_profile == "dependency-free":
        blocked_names = {
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
            "build.xml",
            "gradlew",
            "mvnw",
        }
        if any(
            PurePosixPath(file.path).name in blocked_names
            or PurePosixPath(file.path).suffix.lower() in {".jar", ".kt"}
            for file in manifest.files
        ):
            raise TraceProofError(
                "Java dependency-free profile does not support build descriptors, JARs or Kotlin"
            )
    return scope
