"""Deterministic OSV evaluation over declared components; a match is a candidate, not a verdict."""

import re
from collections import Counter

from veriflow.domain import TraceProofError
from veriflow.maven_version import maven_key
from veriflow.osv_database import OSV_ECOSYSTEMS, package_key

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
EVENT_ORDER = {"introduced": 0, "fixed": 1, "last_affected": 2}
MAX_MATCHES = 10_000
# A version field is untrusted manifest input; bound it before any integer conversion.
MAX_VERSION_CHARS = 256
# Advisory prose is unbounded upstream; cap what a single match can carry.
MAX_SUMMARY_CHARS = 4096
MAX_ALIASES = 50
# A withdrawn advisory is deliberately excluded; every other skip is unread evidence.
SAFE_SKIPS = frozenset({"withdrawn"})
MAX_SYMBOLS = 200
MAX_IMPORT_ENTRIES = 50


def identifier(part):
    return (0, int(part), "") if part.isdigit() else (1, 0, part)


def semver_key(value):
    """Order a version by semantic-version precedence; anything else is not ordered here."""
    if not isinstance(value, str) or len(value) > MAX_VERSION_CHARS:
        return None
    if value.strip() == "0":
        # OSV writes an unbounded lower bound as "0", which is not itself a semantic version.
        return (0, 0, 0, 0, ())
    match = SEMVER.match(value.strip())
    if match is None:
        return None
    major, minor, patch, prerelease = match.groups()
    if prerelease is None:
        return (int(major), int(minor), int(patch), 1, ())
    return (
        int(major),
        int(minor),
        int(patch),
        0,
        tuple(identifier(part) for part in prerelease.split(".")),
    )


def range_events(entry, ordering):
    """Order events by version so the walk below does not depend on how the record was written."""
    events = []
    for event in entry.get("events") or ():
        if not isinstance(event, dict):
            return None
        for kind in EVENT_ORDER:
            if kind in event:
                key = ordering(event[kind])
                if key is None:
                    return None
                events.append((key, EVENT_ORDER[kind], kind))
    return sorted(events, key=lambda item: (item[0], item[1])) or None


def affected_by_range(version_key, entry, ordering):
    events = range_events(entry, ordering)
    if events is None:
        return None
    affected = False
    for key, _, kind in events:
        if kind == "introduced" and version_key >= key:
            affected = True
        elif kind == "fixed" and version_key >= key:
            affected = False
        elif kind == "last_affected" and version_key > key:
            affected = False
    return affected


def ordering_for(range_type, ecosystem):
    """Bind a range type to an ordering; an ecosystem without one is never ordered by guess."""
    if range_type == "SEMVER":
        if ecosystem == "go":
            return go_key, "semver_range", "version_not_semver"
        return semver_key, "semver_range", "version_not_semver"
    if range_type == "ECOSYSTEM" and ecosystem == "maven":
        return maven_key, "maven_range", "version_not_maven"
    return None, None, None


def evaluate_entry(version, entry, ecosystem):
    """Return (matched, basis, gaps); an unordered range is a gap, never an implicit no-match."""
    listed = entry.get("versions")
    forms = {version, version.removeprefix("v")} if ecosystem == "go" else {version}
    if isinstance(listed, list) and forms & set(listed):
        return True, "version_list", Counter()
    gaps = Counter()
    for declared in entry.get("ranges") or ():
        if not isinstance(declared, dict):
            continue
        kind = declared.get("type")
        ordering, basis, unordered = ordering_for(kind, ecosystem)
        if ordering is None:
            label = kind if isinstance(kind, str) else "unknown"
            gaps[f"range_type_{label}_{ecosystem}"] += 1
            continue
        version_key = ordering(version)
        if version_key is None:
            gaps[unordered] += 1
            continue
        result = affected_by_range(version_key, declared, ordering)
        if result is None:
            gaps[f"{basis}_bound_unordered"] += 1
        elif result:
            return True, basis, Counter()
    return False, None, gaps


def module_path(component):
    return (
        f"{component['namespace']}/{component['name']}"
        if component["namespace"]
        else component["name"]
    )


def component_key(component):
    ecosystem = OSV_ECOSYSTEMS.get(component["ecosystem"])
    if ecosystem is None:
        return None
    if component["ecosystem"] == "maven":
        return package_key(ecosystem, f"{component['namespace']}:{component['name']}")
    if component["ecosystem"] == "go":
        return package_key(ecosystem, module_path(component))
    return package_key(ecosystem, component["name"])


def go_key(value):
    # Go versions carry a v prefix; OSV Go ranges are written as plain semantic versions.
    if not isinstance(value, str) or len(value) > MAX_VERSION_CHARS:
        return None
    return semver_key(value.removeprefix("v"))


def severity_of(record):
    severity = record.get("severity")
    return [
        {"type": item["type"], "score": item["score"]}
        for item in (severity if isinstance(severity, list) else ())
        if isinstance(item, dict) and isinstance(item.get("type"), str) and "score" in item
    ]


def affected_imports(entry):
    """Carry the Go vulnerability database's package/symbol data; other ecosystems have none."""
    specific = entry.get("ecosystem_specific")
    listed = specific.get("imports") if isinstance(specific, dict) else None
    imports = []
    for item in listed if isinstance(listed, list) else ():
        path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(path, str) or not path:
            continue
        symbols = item.get("symbols")
        imports.append(
            {
                "path": path,
                "symbols": sorted(
                    s for s in (symbols or ()) if isinstance(s, str) and 0 < len(s) <= 200
                )[:MAX_SYMBOLS],
                "platform_constrained": bool(item.get("goos") or item.get("goarch")),
            }
        )
    return imports[:MAX_IMPORT_ENTRIES]


def match_record(component, record, basis, entry):
    aliases = record.get("aliases")
    summary = record.get("summary")
    summary = summary if isinstance(summary, str) else None
    truncated = summary is not None and len(summary) > MAX_SUMMARY_CHARS
    return {
        "osv_id": record["id"],
        "aliases": sorted(a for a in (aliases or ()) if isinstance(a, str))[:MAX_ALIASES],
        "summary": summary[:MAX_SUMMARY_CHARS] if summary else None,
        "summary_truncated": truncated,
        "severity": severity_of(record),
        "match_basis": basis,
        "component_purl": component["purl"],
        "component_name": component["name"],
        "component_namespace": component["namespace"],
        "component_version": component["version"],
        "component_ref": f"{component['purl']}|{component['resolution']}",
        "ecosystem": component["ecosystem"],
        "affected_imports": (affected_imports(entry) if component["ecosystem"] == "go" else []),
    }


def over_limit(count):
    if count > MAX_MATCHES:
        raise TraceProofError(
            "OSV matches exceed the result limit; no partial vulnerability result was produced"
        )


def evaluate_component(component, index, covered=None, carried=0):
    """Classify one component; absence of a match is only meaningful when nothing was skipped."""
    if component["version"] is None:
        return [], "not_evaluated", Counter(component_state_no_version=1)
    key = component_key(component)
    if key is None:
        return [], "not_evaluated", Counter(component_state_ecosystem_unsupported=1)
    if covered is not None and key[0] not in covered:
        # The export carries no advisories for this ecosystem, so nothing was consulted.
        return [], "not_evaluated", Counter(component_state_ecosystem_not_in_database=1)
    matches, gaps = [], Counter()
    for record, entry in index.get(key, ()):
        matched, basis, entry_gaps = evaluate_entry(
            component["version"], entry, component["ecosystem"]
        )
        gaps += entry_gaps
        if matched:
            matches.append(match_record(component, record, basis, entry))
            over_limit(carried + len(matches))
    if matches:
        return matches, "matched", gaps
    return [], ("partially_evaluated" if gaps else "evaluated_no_match"), gaps


def match_components(components, prepared):
    """Match declared components against a prepared export; no reachability is established."""
    index, loading = prepared["index"], prepared["loading"]
    covered = set(prepared["ecosystems"])
    # Records the loader could not read are unread evidence, not absent evidence, so no
    # component may be reported cleanly against this database.
    unread = sum(
        count for reason, count in loading["records_skipped"].items() if reason not in SAFE_SKIPS
    )
    matches, states, gaps = [], Counter(), Counter()
    for component in components:
        found, state, component_gaps = evaluate_component(component, index, covered, len(matches))
        if unread:
            # Every component was consulted against an incomplete database, matches included.
            component_gaps = component_gaps + Counter(component_state_database_incomplete=1)
            if state == "evaluated_no_match":
                state = "partially_evaluated"
        matches.extend(found)
        states[state] += 1
        gaps += component_gaps
    matches.sort(key=lambda item: (item["component_ref"], item["osv_id"]))
    over_limit(len(matches))
    # No component is fully evaluated when the database itself was not fully read.
    evaluated = 0 if unread else states["matched"] + states["evaluated_no_match"]
    return {
        "matches": matches,
        "coverage": {
            "database_id": prepared["id"],
            "database_source": prepared["source"],
            "database_exported_at": prepared["exported_at"],
            "database_ecosystems": prepared["ecosystems"],
            "database_inventory_sha256": prepared["inventory_sha256"],
            "database_verification": prepared["verification"],
            **loading,
            "components_considered": len(components),
            "components_fully_evaluated": evaluated,
            "component_states": dict(sorted(states.items())),
            "evaluation_gaps": dict(sorted(gaps.items())),
            "match_count": len(matches),
            "database_records_unread": unread,
            "reachability_analysis": "none",
            "version_ordering": "semantic versions; Maven ComparableVersion for Maven ranges",
        },
    }
