"""Bounded lexical import scanning; observed usage prioritizes a candidate and never clears one."""

import hashlib
import re
from collections import Counter
from pathlib import PurePosixPath

NPM_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
MAVEN_SUFFIXES = (".java",)
GO_SUFFIXES = (".go",)
# Installed packages and build output are not first-party source.
EXCLUDED_PARTS = ("node_modules", "target", "build", "dist", "out", "vendor", ".git")
# A bundle inlines its dependencies and would report every one of them as imported.
EXCLUDED_SUFFIXES = (".min.js", ".bundle.js", ".min.mjs")

MAX_SOURCE_FILES = 20_000
MAX_SOURCE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_SPECIFIER = 214

CALL_IMPORT = re.compile(r"\b(?:require|import)\s*\(\s*(['\"])([^'\"\n]{1,214})\1\s*\)")
FROM_IMPORT = re.compile(r"\bfrom\s*(['\"])([^'\"\n]{1,214})\1")
BARE_IMPORT = re.compile(r"\bimport\s*(['\"])([^'\"\n]{1,214})\1")
JAVA_IMPORT = re.compile(
    r"^[ \t]*import[ \t]+(?:static[ \t]+)?([A-Za-z_$][\w$]*(?:\.[A-Za-z_$*][\w$*]*)+)[ \t]*;",
    re.MULTILINE,
)
GO_IMPORT = re.compile(r"\"([A-Za-z0-9][A-Za-z0-9._~!/+-]{0,510})\"")


def first_party(path):
    parts = PurePosixPath(path).parts
    return not any(part in EXCLUDED_PARTS for part in parts[:-1]) and not path.endswith(
        EXCLUDED_SUFFIXES
    )


def language_of(path):
    if path.endswith(NPM_SUFFIXES):
        return "npm"
    if path.endswith(MAVEN_SUFFIXES):
        return "maven"
    return "go" if path.endswith(GO_SUFFIXES) else None


def npm_package(specifier):
    """Reduce an import specifier to its package name; relative and builtin targets are not one."""
    if not specifier or specifier.startswith((".", "/", "node:", "http:", "https:", "data:")):
        return None
    parts = specifier.split("/")
    if parts[0].startswith("@"):
        return "/".join(parts[:2]).lower() if len(parts) > 1 and parts[1] else None
    return parts[0].lower() or None


def npm_specifiers(text):
    found = set()
    for pattern in (CALL_IMPORT, FROM_IMPORT, BARE_IMPORT):
        for match in pattern.finditer(text):
            package = npm_package(match.group(2))
            if package and len(package) <= MAX_SPECIFIER:
                found.add(package)
    return found


def java_imports(text):
    return {match.group(1) for match in JAVA_IMPORT.finditer(text)}


def go_imports(text):
    """Collect quoted paths inside import statements; a package path may be below its module."""
    found, block = set(), False
    for line in text.splitlines():
        body = line.partition("//")[0].strip()
        if block:
            if body.startswith(")"):
                block = False
                continue
            found.update(match.group(1) for match in GO_IMPORT.finditer(body))
            continue
        if body.startswith("import ("):
            block = True
        elif body.startswith("import "):
            found.update(match.group(1) for match in GO_IMPORT.finditer(body))
    return {path for path in found if "/" in path or "." in path}


def read_source(tree, record):
    path = tree / record.path
    if record.size_bytes > MAX_SOURCE_BYTES:
        return None, "oversized"
    try:
        if path.is_symlink():
            return None, "unreadable"
        raw = path.read_bytes()
    except OSError:
        return None, "unreadable"
    if len(raw) != record.size_bytes or hashlib.sha256(raw).hexdigest() != record.sha256:
        return None, "digest_mismatch"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, "not_utf8"


def scan(manifest, tree):
    """Collect import evidence from first-party source only; bundles and vendored trees are out."""
    npm, maven, go, skipped = set(), set(), set(), Counter()
    scanned, total = Counter(), 0
    selected = [
        record
        for record in sorted(manifest.files, key=lambda item: item.path)
        if language_of(record.path) and first_party(record.path)
    ]
    for record in selected[:MAX_SOURCE_FILES]:
        language = language_of(record.path)
        if total + record.size_bytes > MAX_TOTAL_BYTES:
            skipped["total_byte_limit"] += 1
            continue
        text, reason = read_source(tree, record)
        if reason is not None:
            skipped[f"{language}:{reason}"] += 1
            continue
        total += record.size_bytes
        scanned[language] += 1
        if language == "npm":
            npm |= npm_specifiers(text)
        elif language == "maven":
            maven |= java_imports(text)
        else:
            go |= go_imports(text)
    return {
        "npm_packages": npm,
        "java_imports": maven,
        "go_imports": go,
        "files_scanned": dict(sorted(scanned.items())),
        "files_skipped": dict(sorted(skipped.items())),
        "files_available": len(selected),
    }


def usage_of(component, evidence):
    """Positive evidence is meaningful; its absence never establishes that a package is unused."""
    if component["ecosystem"] == "npm":
        if not evidence["files_scanned"].get("npm"):
            return "not_evaluated", None
        if component["name"].lower() in evidence["npm_packages"]:
            return "import_observed", "specifier_exact"
        return "not_observed", None
    if component["ecosystem"] == "go":
        if not evidence["files_scanned"].get("go"):
            return "not_evaluated", None
        path = (
            f"{component['namespace']}/{component['name']}"
            if component["namespace"]
            else component["name"]
        )
        if any(name == path or name.startswith(f"{path}/") for name in evidence["go_imports"]):
            # A Go import path is the module path or a package below it, exactly.
            return "import_observed", "module_path_exact"
        return "not_observed", None
    if component["ecosystem"] == "maven":
        if not evidence["files_scanned"].get("maven"):
            return "not_evaluated", None
        prefix = f"{component['namespace']}."
        if any(name.startswith(prefix) for name in evidence["java_imports"]):
            # groupId-to-package correspondence is a convention, not a guarantee.
            return "import_observed", "group_prefix_conventional"
        return "not_observed", None
    return "not_evaluated", None


def discover_usage(manifest, tree, components):
    """Attach import evidence to declared components; this is not reachability analysis."""
    evidence = scan(manifest, tree)
    states, usage = Counter(), {}
    for component in components:
        state, basis = usage_of(component, evidence)
        states[state] += 1
        usage[f"{component['purl']}|{component['resolution']}"] = {
            "state": state,
            "basis": basis,
        }
    return {
        "usage": usage,
        "coverage": {
            "detection_method": "lexical import scan",
            "analysis": "import evidence only; not reachability",
            "source_files_available": evidence["files_available"],
            "source_files_scanned": evidence["files_scanned"],
            "source_files_skipped": evidence["files_skipped"],
            "usage_states": dict(sorted(states.items())),
            "call_graph_resolved": False,
            "vulnerable_symbol_matching": "none",
            "third_party_source_available": False,
        },
    }
