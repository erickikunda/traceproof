"""OSV-Scanner-shaped result encoding; grouping by declaring file, never a scanner's own output."""

from collections import defaultdict

from veriflow.bundles import canonical
from veriflow.domain import TraceProofError
from veriflow.sbom_export import matched_dependencies

MAX_OSV_BYTES = 8 * 1024 * 1024
LOCKFILE_NAMES = ("package-lock.json", "npm-shrinkwrap.json")


def source_type(path):
    return "lockfile" if path.rsplit("/", 1)[-1] in LOCKFILE_NAMES else "manifest"


def vulnerability(match):
    encoded = {"id": match["osv_id"], "aliases": match["aliases"]}
    if match.get("summary_truncated"):
        encoded["veriflow_summary_truncated"] = True
    if match.get("symbol_state"):
        encoded["veriflow"] = {
            "symbol_evidence": match["symbol_state"],
            "symbols_referenced": match.get("symbols_referenced", []),
        }
    if match["summary"]:
        encoded["summary"] = match["summary"]
    if match["severity"]:
        encoded["severity"] = match["severity"]
    return encoded


def package_name(component):
    """Name a package the way its own ecosystem does, not the way Maven does."""
    if not component["namespace"]:
        return component["name"]
    separator = "/" if component["ecosystem"] == "go" else ":"
    return f"{component['namespace']}{separator}{component['name']}"


def package_entry(component, matches, usage):
    return {
        "package": {
            "name": package_name(component),
            "version": component["version"],
            "ecosystem": component["ecosystem"],
            "purl": component["purl"],
        },
        "vulnerabilities": [vulnerability(match) for match in matches],
        "veriflow": {
            "resolution": component["resolution"],
            "match_bases": sorted({match["match_basis"] for match in matches}),
            **({"usage": usage} if usage is not None else {}),
        },
    }


def export_osv(
    store, repo_id, snapshot_id, database, verify=False, usage=False, cache=False, refresh=False
):
    """Group matches by the file that declared them; an empty group is not a clean result."""
    manifest, discovery, result, evidence, symbols = matched_dependencies(
        store, repo_id, snapshot_id, database, verify, usage, cache, refresh
    )
    by_reference = defaultdict(list)
    for match in result["matches"]:
        by_reference[match["component_ref"]].append(match)
    grouped = defaultdict(list)
    for component in discovery["components"]:
        reference = f"{component['purl']}|{component['resolution']}"
        if reference in by_reference:
            found = evidence["usage"].get(reference) if evidence is not None else None
            for path in component["source_paths"]:
                grouped[path].append(package_entry(component, by_reference[reference], found))
    results, accumulated = [], 0
    for path in sorted(grouped):
        group = {
            "source": {"path": path, "type": source_type(path)},
            "packages": sorted(grouped[path], key=lambda item: item["package"]["purl"]),
        }
        accumulated += len(canonical(group))
        if accumulated > MAX_OSV_BYTES:
            raise TraceProofError(
                "OSV result exceeds the 8 MiB limit; no partial result was produced"
            )
        results.append(group)
    document = {
        "results": results,
        # Not an OSV-Scanner run: coverage below states what was never evaluated.
        "veriflow": {
            "schema_version": "1",
            "snapshot_id": manifest.snapshot_id,
            "repo_id": manifest.repo_id,
            "dependency_coverage": discovery["coverage"],
            "osv_coverage": result["coverage"],
            **({"usage_coverage": evidence["coverage"]} if evidence is not None else {}),
            **({"go_symbol_coverage": symbols["coverage"]} if symbols is not None else {}),
            "limitations": [
                "Matches are candidates; version-range agreement is not exploitability.",
                "No reachability, call-path or runtime evidence supports any match.",
                "Components without a resolved version were never evaluated.",
                "An empty result never means a repository is free of known vulnerabilities.",
                "Import evidence prioritizes a candidate; it never clears or confirms one.",
                "An unimported vulnerable package is not a statement that code is unaffected.",
            ],
        },
    }
    encoded = canonical(document)
    if len(encoded) > MAX_OSV_BYTES:
        raise TraceProofError("OSV result exceeds the 8 MiB limit; no partial result was produced")
    return encoded
