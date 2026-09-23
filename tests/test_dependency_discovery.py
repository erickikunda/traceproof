import json
import zipfile
from uuid import uuid4

import pytest
from conftest import row
from typer.testing import CliRunner

from veriflow.artifacts import ArtifactStore
from veriflow.cli import app
from veriflow.domain import TraceProofError
from veriflow.intake import process, submit
from veriflow.persistence import Run
from veriflow.sbom_export import export_sbom

LOCK_V3 = {
    "name": "app",
    "lockfileVersion": 3,
    "packages": {
        "": {"name": "app", "version": "1.0.0"},
        "node_modules/lodash": {"version": "4.17.21", "integrity": "sha512-lodash"},
        "node_modules/@scope/widget": {"version": "2.0.0"},
        "node_modules/mocha": {"version": "10.2.0", "dev": True},
        "node_modules/fsevents": {"version": "2.3.2", "optional": True},
        "node_modules/lodash/node_modules/nested": {"version": "0.1.0"},
        "node_modules/local-link": {"resolved": "packages/local", "link": True},
    },
}
LOCK_V1 = {
    "name": "app",
    "lockfileVersion": 1,
    "dependencies": {
        "express": {
            "version": "4.18.2",
            "dependencies": {"cookie": {"version": "0.5.0"}},
        }
    },
}
PACKAGE_JSON = {
    "name": "app",
    "dependencies": {"lodash": "^4.17.0"},
    "devDependencies": {"mocha": "~10.2.0"},
}


@pytest.fixture
def snapshot(store, archive, manifest):
    def make(files):
        with zipfile.ZipFile(archive, "w") as out:
            for path, content in files.items():
                raw = content if isinstance(content, str | bytes) else json.dumps(content)
                out.writestr(path, raw)
        batch = submit(store, manifest([row(archive)]), archive.parent, str(uuid4()))
        run_id = process(store, ArtifactStore(store.root), batch)["items"][0]["run_id"]
        with store.transaction() as session:
            run = session.get(Run, run_id)
            return run.repo_id, run.snapshot_id

    return make


def packages_of(store, repo, snapshot_id):
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    return [c for c in document["components"] if c["type"] == "library"]


def properties_of(component):
    return {p["name"]: p["value"] for p in component["properties"]}


def test_lockfile_v3_pins_versions_and_marks_scopes(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    found = {c["purl"]: c for c in packages_of(store, repo, snapshot_id)}
    assert set(found) == {
        "pkg:npm/lodash@4.17.21",
        "pkg:npm/%40scope/widget@2.0.0",
        "pkg:npm/mocha@10.2.0",
        "pkg:npm/fsevents@2.3.2",
        "pkg:npm/nested@0.1.0",
    }
    lodash = found["pkg:npm/lodash@4.17.21"]
    assert lodash["version"] == "4.17.21" and lodash["name"] == "lodash"
    assert properties_of(lodash)["veriflow:resolution"] == "pinned"
    assert properties_of(lodash)["veriflow:npm_integrity"] == "sha512-lodash"
    assert properties_of(found["pkg:npm/mocha@10.2.0"])["veriflow:declared_scopes"] == "dev"
    fsevents = properties_of(found["pkg:npm/fsevents@2.3.2"])
    assert fsevents["veriflow:declared_scopes"] == "optional"


def test_workspace_link_entry_is_not_a_registry_package(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    assert not any("local-link" in c["purl"] for c in packages_of(store, repo, snapshot_id))


def test_lockfile_v1_nested_tree_is_read(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V1})
    assert {c["purl"] for c in packages_of(store, repo, snapshot_id)} == {
        "pkg:npm/express@4.18.2",
        "pkg:npm/cookie@0.5.0",
    }


def test_manifest_range_is_not_a_version(store, snapshot):
    repo, snapshot_id = snapshot({"package.json": PACKAGE_JSON})
    found = {c["purl"]: c for c in packages_of(store, repo, snapshot_id)}
    assert set(found) == {"pkg:npm/lodash", "pkg:npm/mocha"}
    lodash = found["pkg:npm/lodash"]
    assert "version" not in lodash
    properties = properties_of(lodash)
    assert properties["veriflow:resolution"] == "declared_range"
    assert properties["veriflow:version_constraint"] == "^4.17.0"
    assert properties["veriflow:declared_in"] == "package.json"


def test_pinned_and_declared_records_stay_distinct(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3, "package.json": PACKAGE_JSON})
    purls = [c["purl"] for c in packages_of(store, repo, snapshot_id)]
    assert "pkg:npm/lodash@4.17.21" in purls and "pkg:npm/lodash" in purls
    refs = [c["bom-ref"] for c in packages_of(store, repo, snapshot_id)]
    assert len(refs) == len(set(refs))


def test_vendored_manifests_are_ignored(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "package.json": PACKAGE_JSON,
            "node_modules/lodash/package.json": {"name": "lodash", "version": "4.17.21"},
            "node_modules/lodash/index.js": "module.exports = 1\n",
        }
    )
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["veriflow:excluded_declarations_ignored"] == "1"
    assert properties["veriflow:dependency_files_parsed"] == "npm=1"
    # The vendored file is still inventoried as a file; it is just not a declaration.
    assert any(c["name"] == "node_modules/lodash/package.json" for c in document["components"])


def test_unparsable_declaration_is_skipped_and_counted(store, snapshot):
    repo, snapshot_id = snapshot({"package.json": "{not json", "package-lock.json": LOCK_V1})
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["veriflow:dependency_files_skipped"] == "npm:not_json=1"
    assert properties["veriflow:dependency_files_parsed"] == "npm=1"
    assert properties["veriflow:ecosystem_notes"] == "npm_lockfiles_parsed=1"


def test_coverage_records_what_was_not_resolved(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["veriflow:package_resolution"] == "declared"
    assert properties["veriflow:transitive_dependencies"] == "not_resolved"
    assert properties["veriflow:vulnerability_analysis"] == "not_included"
    assert properties["veriflow:dependency_ecosystems"] == "npm"
    assert properties["veriflow:dependency_resolution_counts"] == "pinned=5"
    assert properties["veriflow:inheritance_resolved"] == "false"
    assert "vulnerabilities" not in document


def test_absent_ecosystem_is_not_an_empty_claim(store, snapshot):
    repo, snapshot_id = snapshot({"app.py": "print(1)\n"})
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["veriflow:dependency_ecosystems"] == ""
    assert properties["veriflow:dependency_files_parsed"] == ""
    assert not [c for c in document["components"] if c["type"] == "library"]


def test_packages_are_opt_in_and_deterministic(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    assert not packages_of(store, repo, snapshot_id) == []
    default = json.loads(export_sbom(store, repo, snapshot_id))
    assert not [c for c in default["components"] if c["type"] == "library"]
    assert {p["name"] for p in default["metadata"]["properties"]}.isdisjoint(
        {"veriflow:dependency_ecosystems"}
    )
    first = export_sbom(store, repo, snapshot_id, packages=True)
    assert first == export_sbom(store, repo, snapshot_id, packages=True)


def test_cli_exposes_packages_flag(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    result = CliRunner().invoke(
        app, ["--state-dir", str(store.root), "get-sbom", repo, snapshot_id, "--packages"]
    )
    assert result.exit_code == 0
    assert result.stdout_bytes == export_sbom(store, repo, snapshot_id, packages=True)


def test_declaration_file_limit_refuses(store, snapshot, monkeypatch):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    monkeypatch.setattr("veriflow.dependency_discovery.MAX_DEPENDENCY_FILES", 0)
    with pytest.raises(TraceProofError, match="declaration file limit"):
        export_sbom(store, repo, snapshot_id, packages=True)


def test_component_limit_refuses(store, snapshot, monkeypatch):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    monkeypatch.setattr("veriflow.dependency_discovery.MAX_DEPENDENCY_COMPONENTS", 1)
    with pytest.raises(TraceProofError, match="dependency component limit"):
        export_sbom(store, repo, snapshot_id, packages=True)


def test_oversized_declaration_is_skipped(store, snapshot, monkeypatch):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    monkeypatch.setattr("veriflow.dependency_discovery.MAX_DEPENDENCY_FILE_BYTES", 1)
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["veriflow:dependency_files_skipped"] == "npm:oversized=1"


def test_missing_tree_refuses_rather_than_report_zero(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK_V3})
    tree = store.root / "artifacts" / snapshot_id / "tree"
    tree.chmod(0o700)
    for path in tree.rglob("*"):
        path.chmod(0o600)
        path.unlink()
    tree.rmdir()
    with pytest.raises(TraceProofError, match="unavailable"):
        export_sbom(store, repo, snapshot_id, packages=True)
