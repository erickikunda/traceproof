"""Bounded declaration reading across ecosystems; declared packages are candidates, not a graph."""

import hashlib
from collections import Counter
from pathlib import PurePosixPath

from veriflow import go_modules, maven_poms, npm_manifests
from veriflow.domain import VeriFlowError

ECOSYSTEMS = (npm_manifests, maven_poms, go_modules)

MAX_DEPENDENCY_FILES = 200
MAX_DEPENDENCY_FILE_BYTES = 8 * 1024 * 1024
MAX_DEPENDENCY_COMPONENTS = 20_000
MAX_RECORDED_PATHS = 20


def ecosystem_for(path):
    name = PurePosixPath(path).name
    for module in ECOSYSTEMS:
        if name in module.DECLARATION_NAMES:
            return module
    return None


def excluded(module, path):
    return any(part in module.EXCLUDED_PARTS for part in PurePosixPath(path).parts[:-1])


def declaration_files(manifest):
    """Select declaration files; copies under an install or build directory are not declarations."""
    selected, ignored = [], 0
    for record in sorted(manifest.files, key=lambda item: item.path):
        module = ecosystem_for(record.path)
        if module is None:
            continue
        if excluded(module, record.path):
            ignored += 1
            continue
        selected.append((module, record))
    return selected, ignored


def read_declaration(tree, record):
    path = tree / record.path
    if record.size_bytes > MAX_DEPENDENCY_FILE_BYTES:
        return None, "oversized"
    try:
        if path.is_symlink():
            return None, "unreadable"
        raw = path.read_bytes()
    except OSError:
        return None, "unreadable"
    if len(raw) != record.size_bytes or hashlib.sha256(raw).hexdigest() != record.sha256:
        return None, "digest_mismatch"
    return raw, None


def aggregate(records):
    """Collapse to one component per ecosystem/identity/resolution; order never affects identity."""
    merged = {}
    for record in records:
        key = (record["ecosystem"], record["purl"], record["resolution"])
        entry = merged.setdefault(
            key,
            {
                "ecosystem": record["ecosystem"],
                "name": record["name"],
                "namespace": record["namespace"],
                "version": record["version"],
                "purl": record["purl"],
                "resolution": record["resolution"],
                "scopes": set(),
                "source_paths": set(),
                "constraints": set(),
                "version_sources": set(),
                "integrity": set(),
            },
        )
        entry["scopes"].update(record["scope"].split(","))
        entry["source_paths"].add(record["source_path"])
        for field, target in (("constraint", "constraints"), ("version_source", "version_sources")):
            if record.get(field):
                entry[target].add(record[field])
        if record.get("integrity"):
            entry["integrity"].add(record["integrity"])
    components = []
    for key in sorted(merged):
        entry = merged[key]
        integrity = sorted(entry["integrity"])
        components.append(
            {
                **{k: v for k, v in entry.items() if not isinstance(v, set)},
                "scopes": sorted(entry["scopes"]),
                "source_paths": sorted(entry["source_paths"])[:MAX_RECORDED_PATHS],
                "constraints": sorted(entry["constraints"]),
                "version_sources": sorted(entry["version_sources"]),
                "integrity": integrity[0] if len(integrity) == 1 else None,
            }
        )
    return components


def discover_dependencies(manifest, tree):
    """Read declared packages; this resolves no transitive closure and installs nothing."""
    selected, ignored = declaration_files(manifest)
    if len(selected) > MAX_DEPENDENCY_FILES:
        raise VeriFlowError("Snapshot exceeds the dependency declaration file limit")
    records, parsed, skipped, notes = [], {}, Counter(), Counter()
    for module, record in selected:
        raw, reason = read_declaration(tree, record)
        if reason is None:
            found, reason, extra = module.parse(raw, record.path)
            records.extend(found)
            notes.update({f"{module.ECOSYSTEM}_{k}": v for k, v in extra.items()})
        if reason is not None:
            skipped[f"{module.ECOSYSTEM}:{reason}"] += 1
            continue
        parsed.setdefault(module.ECOSYSTEM, []).append(record.path)
    components = aggregate(records)
    if len(components) > MAX_DEPENDENCY_COMPONENTS:
        raise VeriFlowError("Snapshot exceeds the dependency component limit")
    coverage = {
        "ecosystems": sorted(parsed),
        "declaration_files_parsed": {key: sorted(value) for key, value in sorted(parsed.items())},
        "declaration_files_skipped": dict(sorted(skipped.items())),
        "excluded_declarations_ignored": ignored,
        "ecosystem_notes": dict(sorted(notes.items())),
        "transitive_resolved": False,
        "registry_resolution": "none",
        "inheritance_resolved": False,
        "component_count": len(components),
        "resolution_counts": dict(sorted(Counter(c["resolution"] for c in components).items())),
    }
    return {"components": components, "coverage": coverage}
