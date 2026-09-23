"""Pinned operator-supplied OSV export loading; nothing is fetched, updated or resolved online."""

import hashlib
import json
from pathlib import Path, PurePosixPath

from veriflow.bundles import canonical
from veriflow.domain import VeriFlowError

MAX_PROFILE_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 2 * 1024 * 1024
# A full npm export alone carries over 229,000 advisories; the byte caps are the real backstop.
MAX_RECORDS = 500_000
# OSV names an ecosystem differently from the declaration parsers.
OSV_ECOSYSTEMS = {"npm": "npm", "maven": "Maven", "go": "Go"}
PROFILE_FIELDS = {
    "version",
    "source",
    "exported_at",
    "ecosystems",
    "records_directory",
    "record_count",
    "inventory_sha256",
}


def record_inventory(root):
    """Digest every record file; a symbolic link is refused rather than followed."""
    listing = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise VeriFlowError("OSV database cannot contain symbolic links")
        if path.is_file():
            if len(listing) >= MAX_RECORDS:
                raise VeriFlowError("OSV database exceeds the record inventory limit")
            with path.open("rb") as handle:
                listing[path.relative_to(root).as_posix()] = hashlib.file_digest(
                    handle, "sha256"
                ).hexdigest()
    return listing


def read_profile(path):
    """Parse and validate the profile alone; the record inventory is not read here."""
    path = Path(path).resolve(strict=True)
    with path.open("rb") as handle:
        raw = handle.read(MAX_PROFILE_BYTES + 1)
    try:
        if len(raw) > MAX_PROFILE_BYTES:
            raise ValueError()
        profile = json.loads(raw)
        if set(profile) != PROFILE_FIELDS or profile["version"] != "1":
            raise ValueError()
        for field in ("source", "exported_at", "records_directory", "inventory_sha256"):
            if not isinstance(profile[field], str) or not 0 < len(profile[field]) <= 400:
                raise ValueError()
        ecosystems = profile["ecosystems"]
        if not isinstance(ecosystems, list) or not set(ecosystems) <= set(OSV_ECOSYSTEMS.values()):
            raise ValueError()
        count = profile["record_count"]
        if type(count) is not int or not 0 <= count <= MAX_RECORDS:
            raise ValueError()
        relative = PurePosixPath(profile["records_directory"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative):
            raise ValueError()
        root = (path.parent / relative).resolve(strict=True)
        if not root.is_relative_to(path.parent) or not root.is_dir():
            raise ValueError()
    except (ValueError, TypeError, KeyError, AttributeError, OSError):
        raise VeriFlowError("Invalid OSV database profile") from None
    return {
        "id": hashlib.sha256(raw).hexdigest(),
        "source": profile["source"],
        "exported_at": profile["exported_at"],
        "ecosystems": sorted(ecosystems),
        "inventory_sha256": profile["inventory_sha256"],
        "record_count": count,
        "root": root,
    }


def load_profile(path):
    """Verify an operator-authored export against one pinned inventory digest."""
    profile = read_profile(path)
    listing = record_inventory(profile["root"])
    if len(listing) != profile["record_count"]:
        raise VeriFlowError("OSV database record count does not match its inventory")
    if hashlib.sha256(canonical(listing)).hexdigest() != profile["inventory_sha256"]:
        raise VeriFlowError("OSV database integrity mismatch")
    return {**profile, "listing": listing}


def read_record(root, relative):
    path = root / relative
    try:
        if path.is_symlink():
            return None, "unreadable"
        with path.open("rb") as handle:
            raw = handle.read(MAX_RECORD_BYTES + 1)
    except OSError:
        return None, "unreadable"
    if len(raw) > MAX_RECORD_BYTES:
        return None, "oversized"
    try:
        record = json.loads(raw)
    except ValueError:
        return None, "not_json"
    if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"]:
        return None, "unrecognized_shape"
    if record.get("withdrawn"):
        # A withdrawn advisory is not evidence of anything; it must never match.
        return None, "withdrawn"
    if not valid_record(record):
        # Structure matching depends on; a malformed record is unread, never empty evidence.
        return None, "unrecognized_shape"
    return record, None


def strings(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def valid_range(declared):
    if not isinstance(declared, dict):
        return False
    if "type" in declared and not isinstance(declared["type"], str):
        return False
    events = declared.get("events")
    if events is None:
        return True
    return isinstance(events, list) and all(
        isinstance(event, dict) and all(isinstance(v, str) for v in event.values())
        for event in events
    )


def valid_affected(entry):
    """Validate the nested shape matching reads, so malformed data is unread, not absent."""
    if not isinstance(entry, dict):
        return False
    package = entry.get("package")
    if package is not None:
        if not isinstance(package, dict):
            return False
        for field in ("ecosystem", "name"):
            if field in package and not isinstance(package[field], str):
                return False
    if "versions" in entry and not strings(entry["versions"]):
        return False
    ranges = entry.get("ranges")
    if ranges is not None and (
        not isinstance(ranges, list) or not all(valid_range(item) for item in ranges)
    ):
        return False
    specific = entry.get("ecosystem_specific")
    return specific is None or isinstance(specific, dict)


def valid_record(record):
    affected = record.get("affected")
    if affected is None:
        return True
    if not isinstance(affected, list):
        return False
    return all(valid_affected(entry) for entry in affected)


def package_key(ecosystem, name):
    return (ecosystem, name.lower() if ecosystem == "npm" else name)


def build_index(profile):
    """Index affected entries by package; a withdrawn or malformed record is counted only."""
    index, skipped, loaded, seen = {}, {}, 0, set()
    for relative in sorted(profile["listing"]):
        record, reason = read_record(profile["root"], relative)
        if reason is not None:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        if record["id"] in seen:
            # One advisory indexed twice would report the same candidate twice.
            skipped["duplicate_id"] = skipped.get("duplicate_id", 0) + 1
            continue
        seen.add(record["id"])
        loaded += 1
        affected = record.get("affected")
        for entry in affected if isinstance(affected, list) else ():
            package = entry.get("package") if isinstance(entry, dict) else None
            if not isinstance(package, dict):
                continue
            ecosystem, name = package.get("ecosystem"), package.get("name")
            if not isinstance(ecosystem, str) or not isinstance(name, str) or not name:
                continue
            # OSV qualifies some ecosystems with a release, as in "Debian:11".
            index.setdefault(package_key(ecosystem.split(":")[0], name), []).append((record, entry))
    return index, {"records_loaded": loaded, "records_skipped": dict(sorted(skipped.items()))}


CACHE_SCHEMA = "1"
MAX_CACHE_BYTES = 1024 * 1024 * 1024
# Only the fields matching reads; details, references and credits are deliberately dropped.
RECORD_FIELDS = ("id", "aliases", "summary", "severity")
ENTRY_FIELDS = ("versions", "ranges", "ecosystem_specific")


def compact(value, fields):
    return {field: value[field] for field in fields if value.get(field) is not None}


def cache_path(root, profile):
    return Path(root) / "osv-cache" / f"{profile['id']}.json"


def cache_payload(profile, index, loading):
    packages = {}
    for (ecosystem, name), entries in index.items():
        packages.setdefault(ecosystem, {})[name] = [
            [compact(record, RECORD_FIELDS), compact(entry, ENTRY_FIELDS)]
            for record, entry in entries
        ]
    return {
        "schema_version": CACHE_SCHEMA,
        "inventory_sha256": profile["inventory_sha256"],
        "record_count": profile["record_count"],
        "loading": loading,
        "packages": packages,
    }


def write_cache(root, profile, index, loading):
    """Derived state only; a cache is written from a fully verified load, never from another."""
    path = cache_path(root, profile)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        encoded = canonical(cache_payload(profile, index, loading))
        if len(encoded) > MAX_CACHE_BYTES:
            return None
        temporary = path.with_suffix(".partial")
        temporary.write_bytes(encoded)
        temporary.replace(path)
    except OSError:
        # A cache is an optimisation; failing to write one must never fail the scan.
        return None
    return path


def read_cache(root, profile):
    """Accept a cache only when it names the inventory digest this profile pins."""
    path = cache_path(root, profile)
    try:
        if path.is_symlink():
            return None
        with path.open("rb") as handle:
            raw = handle.read(MAX_CACHE_BYTES + 1)
    except OSError:
        return None
    if len(raw) > MAX_CACHE_BYTES:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != CACHE_SCHEMA
        or payload.get("inventory_sha256") != profile["inventory_sha256"]
        or payload.get("record_count") != profile["record_count"]
        or not isinstance(payload.get("packages"), dict)
        or not isinstance(payload.get("loading"), dict)
    ):
        return None
    index = {}
    for ecosystem, names in payload["packages"].items():
        if not isinstance(names, dict):
            return None
        for name, entries in names.items():
            index[(ecosystem, name)] = [
                (pair[0], pair[1])
                for pair in entries
                if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], dict)
            ]
    return index, payload["loading"]


def prepare(path, cache_root=None, refresh=False):
    """Load a database for matching; a cache trades inventory re-verification for speed."""
    if cache_root is not None and not refresh:
        profile = read_profile(path)
        cached = read_cache(cache_root, profile)
        if cached is not None:
            index, loading = cached
            return {**profile, "index": index, "loading": loading, "verification": "cached"}
    profile = load_profile(path)
    index, loading = build_index(profile)
    if cache_root is not None:
        write_cache(cache_root, profile, index, loading)
    return {**profile, "index": index, "loading": loading, "verification": "reverified"}
