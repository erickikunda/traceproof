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
    "python": LanguageAdapter(
        "python", "python", "python-source-v1", "python_ast", "python_claims"
    ),
    "java": LanguageAdapter(
        "java", "java", "java-dependency-free-v1", "not_qualified", "unsupported"
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
        raise TraceProofError("Implemented extraction languages are python and java")
    return ADAPTERS[language]


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


def validate_extraction_scope(manifest, language):
    scope = language_scope(manifest, language)
    if not scope["selected_file_count"]:
        raise TraceProofError("Snapshot contains no files for the selected language")
    if language == "java":
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
