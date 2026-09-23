import json

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from veriflow.cli import app
from veriflow.domain import TraceProofError
from veriflow.persistence import Run, Snapshot
from veriflow.sbom_export import export_sbom


def snapshot_of(store, run_id):
    with store.transaction() as session:
        return session.get(Run, run_id).snapshot_id


def test_file_inventory_shape_and_cli(store, scanned):
    repo, run, _, _ = scanned
    snapshot_id = snapshot_of(store, run)
    raw = export_sbom(store, repo, snapshot_id)
    document = json.loads(raw)
    assert document["bomFormat"] == "CycloneDX" and document["specVersion"] == "1.6"
    assert document["metadata"]["component"]["version"] == snapshot_id
    assert document["metadata"]["component"]["name"] == repo
    assert [c["name"] for c in document["components"]] == ["app.py"]
    assert document["components"][0]["type"] == "file"
    assert document["components"][0]["hashes"][0]["alg"] == "SHA-256"
    result = CliRunner().invoke(
        app, ["--state-dir", str(store.root), "get-sbom", repo, snapshot_id]
    )
    assert result.exit_code == 0 and result.stdout_bytes == raw


def test_hashes_match_the_recorded_manifest(store, scanned):
    repo, run, _, _ = scanned
    snapshot_id = snapshot_of(store, run)
    document = json.loads(export_sbom(store, repo, snapshot_id))
    with store.transaction() as session:
        files = session.get(Snapshot, snapshot_id).manifest["files"]
    recorded = {record["path"]: record["sha256"] for record in files}
    emitted = {c["name"]: c["hashes"][0]["content"] for c in document["components"]}
    assert emitted == recorded
    sizes = {c["name"]: c["properties"][0]["value"] for c in document["components"]}
    assert sizes == {record["path"]: str(record["size_bytes"]) for record in files}


def test_export_is_deterministic_and_has_no_timestamp(store, scanned):
    repo, run, _, _ = scanned
    snapshot_id = snapshot_of(store, run)
    assert export_sbom(store, repo, snapshot_id) == export_sbom(store, repo, snapshot_id)
    document = json.loads(export_sbom(store, repo, snapshot_id))
    assert "timestamp" not in document["metadata"]
    assert document["serialNumber"].startswith("urn:uuid:")


def test_no_vulnerability_or_package_claim(store, scanned):
    repo, run, _, _ = scanned
    document = json.loads(export_sbom(store, repo, snapshot_of(store, run)))
    assert "vulnerabilities" not in document
    assert all(c["type"] == "file" for c in document["components"])
    assert not any("purl" in c for c in document["components"])
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["veriflow:package_resolution"] == "none"
    assert properties["veriflow:transitive_dependencies"] == "not_resolved"
    assert properties["veriflow:vulnerability_analysis"] == "not_included"
    assert properties["veriflow:license_inventory"] == "not_established"
    assert properties["veriflow:manifest_verification"] == "recorded"


def test_reverification_is_opt_in_and_reported(store, scanned):
    repo, run, _, _ = scanned
    snapshot_id = snapshot_of(store, run)
    document = json.loads(export_sbom(store, repo, snapshot_id, verify=True))
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["veriflow:manifest_verification"] == "reverified"
    recorded = json.loads(export_sbom(store, repo, snapshot_id))
    assert [c["bom-ref"] for c in document["components"]] == [
        c["bom-ref"] for c in recorded["components"]
    ]


def test_reverification_detects_a_changed_tree(store, scanned):
    repo, run, _, _ = scanned
    snapshot_id = snapshot_of(store, run)
    source = store.root / "artifacts" / snapshot_id / "tree" / "app.py"
    source.chmod(0o600)
    source.write_text("def f(x):\n    return x\n")
    assert export_sbom(store, repo, snapshot_id)
    with pytest.raises(TraceProofError, match="digest"):
        export_sbom(store, repo, snapshot_id, verify=True)


def test_other_repository_cannot_export(store, scanned):
    repo, run, _, _ = scanned
    snapshot_id = snapshot_of(store, run)
    with pytest.raises(TraceProofError, match="belong"):
        export_sbom(store, "other-repo", snapshot_id)
    result = CliRunner().invoke(
        app, ["--state-dir", str(store.root), "get-sbom", "other-repo", snapshot_id]
    )
    assert result.exit_code == 1 and result.stdout_bytes == b""


def test_unknown_snapshot_is_refused(store, scanned):
    repo, _, _, _ = scanned
    with pytest.raises(TraceProofError, match="belong"):
        export_sbom(store, repo, "0" * 64)


def test_component_limit_refuses_a_partial_document(store, scanned, monkeypatch):
    repo, run, _, _ = scanned
    monkeypatch.setattr("veriflow.sbom_export.MAX_SBOM_COMPONENTS", 0)
    with pytest.raises(TraceProofError, match="component limit"):
        export_sbom(store, repo, snapshot_of(store, run))


def test_byte_limit_refuses_a_partial_document(store, scanned, monkeypatch):
    repo, run, _, _ = scanned
    monkeypatch.setattr("veriflow.sbom_export.MAX_SBOM_BYTES", 1)
    with pytest.raises(TraceProofError, match="8 MiB"):
        export_sbom(store, repo, snapshot_of(store, run))


def test_invalid_manifest_record_is_refused(store, scanned):
    repo, run, _, _ = scanned
    snapshot_id = snapshot_of(store, run)
    with store.transaction() as session:
        record = session.get(Snapshot, snapshot_id)
        record.manifest = {**record.manifest, "files": [{"path": "../escape", "sha256": "x"}]}
    with pytest.raises(TraceProofError, match="invalid"):
        export_sbom(store, repo, snapshot_id)
