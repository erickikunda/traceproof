"""Deterministic CycloneDX file inventory for a snapshot; components are files, not packages."""

import uuid

from sqlalchemy import select

from veriflow.bundles import canonical
from veriflow.dependency_discovery import discover_dependencies
from veriflow.dependency_usage import discover_usage
from veriflow.domain import SnapshotManifest, TraceProofError
from veriflow.go_symbols import evaluate_symbols
from veriflow.osv_database import prepare
from veriflow.osv_matching import match_components
from veriflow.persistence import Snapshot

MAX_SBOM_COMPONENTS = 20_000
MAX_SBOM_BYTES = 8 * 1024 * 1024
SPEC_VERSION = "1.6"
# Fixed namespace so an identical snapshot always yields an identical serial number.
SERIAL_NAMESPACE = uuid.UUID("6b4d3f2a-9c1e-4a77-8f0b-2d5e7c8a1b34")


def recorded_manifest(store, repo_id, snapshot_id):
    with store.transaction() as session:
        snapshot = session.scalar(
            select(Snapshot).where(Snapshot.id == snapshot_id, Snapshot.repo_id == repo_id)
        )
        if snapshot is None:
            raise TraceProofError("Snapshot does not belong to repository")
        record = snapshot.manifest
    try:
        manifest = SnapshotManifest.model_validate(record)
    except ValueError:
        raise TraceProofError("Snapshot manifest record is invalid; no SBOM was produced") from None
    if manifest.snapshot_id != snapshot_id:
        raise TraceProofError("Snapshot manifest record does not match its identity")
    return manifest


def reverified_manifest(store, repo_id, snapshot_id):
    from veriflow.artifacts import ArtifactStore

    recorded = recorded_manifest(store, repo_id, snapshot_id)
    manifest = ArtifactStore(store.root).verify(snapshot_id)
    if manifest.model_dump(mode="json") != recorded.model_dump(mode="json"):
        raise TraceProofError("Snapshot manifest differs from its admitted database record")
    return manifest


def component(record):
    return {
        "type": "file",
        "bom-ref": f"file:{record.sha256}:{record.path}",
        "name": record.path,
        "hashes": [{"alg": "SHA-256", "content": record.sha256}],
        "properties": [{"name": "veriflow:size_bytes", "value": str(record.size_bytes)}],
    }


def package_component(entry, usage=None):
    """Encode a declared package; npm integrity is a registry digest, not verified here."""
    properties = [
        {"name": "veriflow:ecosystem", "value": entry["ecosystem"]},
        {"name": "veriflow:resolution", "value": entry["resolution"]},
        {"name": "veriflow:declared_scopes", "value": ",".join(entry["scopes"])},
        {"name": "veriflow:declared_in", "value": ",".join(entry["source_paths"])},
    ]
    if entry["version_sources"]:
        properties.append(
            {"name": "veriflow:version_source", "value": ",".join(entry["version_sources"])}
        )
    if entry["constraints"]:
        properties.append(
            {"name": "veriflow:version_constraint", "value": ",".join(entry["constraints"])}
        )
    if entry["integrity"]:
        properties.append({"name": "veriflow:npm_integrity", "value": entry["integrity"]})
    if usage is not None:
        properties.append({"name": "veriflow:usage_state", "value": usage["state"]})
        if usage["basis"]:
            properties.append({"name": "veriflow:usage_basis", "value": usage["basis"]})
    encoded = {
        "type": "library",
        "bom-ref": f"{entry['purl']}|{entry['resolution']}",
        "name": entry["name"],
        "purl": entry["purl"],
        "properties": properties,
    }
    if entry["namespace"]:
        encoded["group"] = entry["namespace"]
    # A range or an inherited version is not a component version; omit rather than assert one.
    return {**encoded, "version": entry["version"]} if entry["version"] else encoded


def counted(mapping):
    return ",".join(f"{key}={value}" for key, value in mapping.items())


def coverage_properties(coverage):
    properties = [
        {"name": "veriflow:dependency_ecosystems", "value": ",".join(coverage["ecosystems"])},
        {
            "name": "veriflow:dependency_files_parsed",
            "value": counted({k: len(v) for k, v in coverage["declaration_files_parsed"].items()}),
        },
        {
            "name": "veriflow:dependency_files_skipped",
            "value": counted(coverage["declaration_files_skipped"]),
        },
        {
            "name": "veriflow:excluded_declarations_ignored",
            "value": str(coverage["excluded_declarations_ignored"]),
        },
        {
            "name": "veriflow:dependency_resolution_counts",
            "value": counted(coverage["resolution_counts"]),
        },
        {"name": "veriflow:inheritance_resolved", "value": "false"},
    ]
    if coverage["ecosystem_notes"]:
        properties.append(
            {"name": "veriflow:ecosystem_notes", "value": counted(coverage["ecosystem_notes"])}
        )
    return properties


def vulnerability(match):
    """Encode a match as in_triage; TraceProof never establishes exploitability from a match."""
    encoded = {
        "bom-ref": f"osv:{match['osv_id']}|{match['component_ref']}",
        "id": match["osv_id"],
        "source": {"name": "OSV"},
        "affects": [{"ref": match["component_ref"]}],
        "analysis": {
            "state": "in_triage",
            "detail": f"Version-range match on {match['match_basis']}; no reachability analysis.",
        },
        "properties": [{"name": "veriflow:match_basis", "value": match["match_basis"]}],
    }
    if match.get("usage_state"):
        # Usage prioritizes a candidate; the analysis state stays in_triage regardless.
        encoded["properties"].append(
            {"name": "veriflow:usage_state", "value": match["usage_state"]}
        )
    if match.get("symbol_state"):
        encoded["properties"].append(
            {"name": "veriflow:go_symbol_evidence", "value": match["symbol_state"]}
        )
        if match.get("symbols_referenced"):
            encoded["properties"].append(
                {
                    "name": "veriflow:go_symbols_referenced",
                    "value": ",".join(match["symbols_referenced"]),
                }
            )
    if match["aliases"]:
        encoded["references"] = [
            {"id": alias, "source": {"name": "OSV"}} for alias in match["aliases"]
        ]
    if match["severity"]:
        encoded["ratings"] = [
            {"method": item["type"], "vector": item["score"]} for item in match["severity"]
        ]
    if match["summary"]:
        encoded["description"] = match["summary"]
    return encoded


def usage_properties(coverage):
    return [
        {"name": "veriflow:usage_detection_method", "value": coverage["detection_method"]},
        {"name": "veriflow:usage_analysis", "value": coverage["analysis"]},
        {
            "name": "veriflow:usage_files_scanned",
            "value": counted(coverage["source_files_scanned"]),
        },
        {
            "name": "veriflow:usage_files_skipped",
            "value": counted(coverage["source_files_skipped"]),
        },
        {"name": "veriflow:usage_states", "value": counted(coverage["usage_states"])},
        {"name": "veriflow:usage_call_graph_resolved", "value": "false"},
        {"name": "veriflow:usage_vulnerable_symbol_matching", "value": "none"},
    ]


def symbol_properties(coverage):
    return [
        {"name": "veriflow:go_symbol_analysis", "value": coverage["analysis"]},
        {"name": "veriflow:go_symbol_states", "value": counted(coverage["symbol_states"])},
        {
            "name": "veriflow:go_advisories_with_symbol_data",
            "value": str(coverage["advisories_with_symbol_data"]),
        },
        {
            "name": "veriflow:go_dot_imports_unresolvable",
            "value": str(coverage["dot_imports_unresolvable"]),
        },
        {"name": "veriflow:go_platform_filtering", "value": "none"},
    ]


def osv_properties(coverage):
    return [
        {"name": "veriflow:osv_database_id", "value": coverage["database_id"]},
        {
            "name": "veriflow:osv_database_verification",
            "value": coverage["database_verification"],
        },
        {"name": "veriflow:osv_database_exported_at", "value": coverage["database_exported_at"]},
        {
            "name": "veriflow:osv_records_loaded",
            "value": str(coverage["records_loaded"]),
        },
        {
            "name": "veriflow:osv_records_unread",
            "value": str(coverage["database_records_unread"]),
        },
        {
            "name": "veriflow:osv_components_fully_evaluated",
            "value": str(coverage["components_fully_evaluated"]),
        },
        {
            "name": "veriflow:osv_component_states",
            "value": counted(coverage["component_states"]),
        },
        {"name": "veriflow:osv_evaluation_gaps", "value": counted(coverage["evaluation_gaps"])},
        {"name": "veriflow:osv_reachability_analysis", "value": "none"},
    ]


def document(manifest, verification, discovery=None, osv=None, usage=None, symbols=None):
    components = [component(record) for record in sorted(manifest.files, key=lambda r: r.path)]
    extra = []
    if discovery is not None:
        references = usage["usage"] if usage is not None else {}
        components += [
            package_component(entry, references.get(f"{entry['purl']}|{entry['resolution']}"))
            for entry in discovery["components"]
        ]
        extra = coverage_properties(discovery["coverage"])
    if usage is not None:
        extra += usage_properties(usage["coverage"])
    if symbols is not None:
        extra += symbol_properties(symbols["coverage"])
    if osv is not None:
        extra += osv_properties(osv["coverage"])
    return {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        # Derived from the snapshot, never generated, so identical input gives identical bytes.
        "serialNumber": f"urn:uuid:{uuid.uuid5(SERIAL_NAMESPACE, manifest.snapshot_id)}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": f"snapshot:{manifest.snapshot_id}",
                "name": manifest.repo_id,
                "version": manifest.snapshot_id,
                "hashes": [{"alg": "SHA-256", "content": manifest.archive_sha256}],
            },
            # A publication timestamp is omitted deliberately; it would break determinism.
            "properties": [
                {"name": "veriflow:classification", "value": manifest.classification},
                {"name": "veriflow:archive_sha256", "value": manifest.archive_sha256},
                {
                    "name": "veriflow:archive_size_bytes",
                    "value": str(manifest.archive_size_bytes),
                },
                {"name": "veriflow:inventory_scope", "value": "snapshot files"},
                {"name": "veriflow:manifest_verification", "value": verification},
                {
                    "name": "veriflow:package_resolution",
                    "value": "declared" if discovery is not None else "none",
                },
                {"name": "veriflow:transitive_dependencies", "value": "not_resolved"},
                {"name": "veriflow:license_inventory", "value": "not_established"},
                {
                    "name": "veriflow:vulnerability_analysis",
                    "value": ("osv_version_range_matching" if osv is not None else "not_included"),
                },
            ]
            + extra,
        },
        "components": components,
        **(
            {"vulnerabilities": [vulnerability(match) for match in osv["matches"]]}
            if osv is not None
            else {}
        ),
    }


def attach_evidence(matches, evidence, symbols):
    for match in matches:
        if evidence is not None:
            match["usage_state"] = evidence["usage"].get(match["component_ref"], {}).get("state")
        if symbols is not None:
            found = symbols["symbol_evidence"].get(f"{match['osv_id']}|{match['component_ref']}")
            if found:
                match["symbol_state"] = found["state"]
                match["symbols_referenced"] = found["symbols_referenced"]


def snapshot_tree(store, snapshot_id):
    from veriflow.artifacts import ArtifactStore

    tree = ArtifactStore(store.root).path(snapshot_id) / "tree"
    if tree.is_symlink() or not tree.is_dir():
        raise TraceProofError("Snapshot source tree is unavailable; check local retention")
    return tree


def matched_dependencies(
    store, repo_id, snapshot_id, database, verify=False, usage=False, cache=False, refresh=False
):
    """Evaluate declared packages against a pinned export; nothing here proves exploitability."""
    store.require_initialized()
    manifest = (
        reverified_manifest(store, repo_id, snapshot_id)
        if verify
        else recorded_manifest(store, repo_id, snapshot_id)
    )
    tree = snapshot_tree(store, snapshot_id)
    discovery = discover_dependencies(manifest, tree)
    evidence = discover_usage(manifest, tree, discovery["components"]) if usage else None
    result = match_components(
        discovery["components"], prepare(database, store.root if cache else None, refresh)
    )
    symbols = evaluate_symbols(manifest, tree, result["matches"]) if usage else None
    attach_evidence(result["matches"], evidence, symbols)
    return manifest, discovery, result, evidence, symbols


def export_sbom(
    store,
    repo_id,
    snapshot_id,
    verify=False,
    packages=False,
    database=None,
    usage=False,
    cache=False,
    refresh=False,
):
    """Re-encode a recorded snapshot manifest; declared packages are candidates only."""
    store.require_initialized()
    if database is not None and not packages:
        raise TraceProofError("Matching OSV records requires --packages")
    if usage and not packages:
        raise TraceProofError("Import evidence requires --packages")
    manifest = (
        reverified_manifest(store, repo_id, snapshot_id)
        if verify
        else recorded_manifest(store, repo_id, snapshot_id)
    )
    if len(manifest.files) > MAX_SBOM_COMPONENTS:
        raise TraceProofError("Snapshot exceeds the SBOM component limit; no partial SBOM written")
    tree = snapshot_tree(store, snapshot_id) if packages else None
    discovery = discover_dependencies(manifest, tree) if packages else None
    evidence = discover_usage(manifest, tree, discovery["components"]) if usage else None
    osv = (
        match_components(
            discovery["components"], prepare(database, store.root if cache else None, refresh)
        )
        if database is not None
        else None
    )
    symbols = (
        evaluate_symbols(manifest, tree, osv["matches"])
        if osv is not None and evidence is not None
        else None
    )
    if osv is not None:
        attach_evidence(osv["matches"], evidence, symbols)
    encoded = canonical(
        document(
            manifest, "reverified" if verify else "recorded", discovery, osv, evidence, symbols
        )
    )
    if len(encoded) > MAX_SBOM_BYTES:
        raise TraceProofError("SBOM exceeds the 8 MiB limit; no partial SBOM was written")
    return encoded
