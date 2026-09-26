"""Bounded npm lockfile/manifest reading; a lockfile records what npm resolved, not what runs."""

import json
from pathlib import PurePosixPath

ECOSYSTEM = "npm"
LOCK_NAMES = ("package-lock.json", "npm-shrinkwrap.json")
MANIFEST_NAMES = ("package.json",)
DECLARATION_NAMES = LOCK_NAMES + MANIFEST_NAMES
# Manifests here are installed copies, not declarations.
EXCLUDED_PARTS = ("node_modules",)
RANGE_FIELDS = {
    "dependencies": "runtime",
    "devDependencies": "dev",
    "optionalDependencies": "optional",
    "peerDependencies": "peer",
}


def encoded_name(name):
    scope, _, bare = name.partition("/")
    if not bare:
        return name.lower()
    # Package URL carries an npm scope as a percent-encoded namespace segment.
    return f"{scope.replace('@', '%40').lower()}/{bare.lower()}"


def purl(name, version):
    reference = f"pkg:npm/{encoded_name(name)}"
    return f"{reference}@{version}" if version else reference


def valid_name(name):
    return (
        isinstance(name, str)
        and 0 < len(name) <= 214
        and "\\" not in name
        and ".." not in name.split("/")
        and name.count("/") <= 1
        and not name.startswith("/")
    )


def lockfile_name(key):
    """Recover a package name from a lockfile path key; nesting keeps the innermost name."""
    parts = PurePosixPath(key).parts
    if "node_modules" not in parts:
        return None
    tail = parts[len(parts) - 1 - parts[::-1].index("node_modules") + 1 :]
    if not tail:
        return None
    return "/".join(tail[:2]) if tail[0].startswith("@") and len(tail) > 1 else tail[0]


def lock_entries(data):
    """Prefer the lockfile v2/v3 packages map; fall back to the v1 nested dependencies tree."""
    packages = data.get("packages")
    if isinstance(packages, dict):
        for key, entry in packages.items():
            if not key or not isinstance(entry, dict) or entry.get("link") is True:
                continue
            name = entry.get("name") if valid_name(entry.get("name")) else lockfile_name(key)
            if valid_name(name):
                yield name, entry
        return
    pending = [data.get("dependencies")]
    while pending:
        current = pending.pop()
        if not isinstance(current, dict):
            continue
        for name, entry in current.items():
            if isinstance(entry, dict) and valid_name(name):
                yield name, entry
                pending.append(entry.get("dependencies"))


def scope_of(entry):
    if entry.get("dev") is True:
        return "dev"
    return "optional" if entry.get("optional") is True else "runtime"


def record(name, version, resolution, scope, source, **extra):
    return {
        "ecosystem": ECOSYSTEM,
        "name": name,
        "namespace": None,
        "version": version,
        "purl": purl(name, version),
        "resolution": resolution,
        "scope": scope,
        "source_path": source,
        **extra,
    }


def parse_lock(data, source):
    records = []
    for name, entry in lock_entries(data):
        version = entry.get("version")
        if isinstance(version, str) and version:
            integrity = entry.get("integrity")
            records.append(
                record(
                    name,
                    version,
                    "pinned",
                    scope_of(entry),
                    source,
                    integrity=integrity if isinstance(integrity, str) else None,
                )
            )
    return records


def parse_ranges(data, source):
    records = []
    for field, scope in RANGE_FIELDS.items():
        declared = data.get(field)
        if not isinstance(declared, dict):
            continue
        for name, constraint in declared.items():
            if valid_name(name) and isinstance(constraint, str):
                records.append(
                    record(name, None, "declared_range", scope, source, constraint=constraint)
                )
    return records


def parse(raw, source):
    try:
        data = json.loads(raw)
    except ValueError:
        return [], "not_json", {}
    if not isinstance(data, dict):
        return [], "unrecognized_shape", {}
    if PurePosixPath(source).name in LOCK_NAMES:
        return parse_lock(data, source), None, {"lockfiles_parsed": 1}
    return parse_ranges(data, source), None, {}
