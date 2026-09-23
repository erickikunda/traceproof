import json
from uuid import uuid4

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.persistence import exclusive_worker
from veriflow.storage_audit import storage_audit


def test_references_sizes_and_no_deletion(store, scanned):
    orphan = store.root / "scans" / str(uuid4())
    orphan.mkdir()
    (orphan / "data").write_bytes(b"abc")
    stage = store.root / "artifacts" / ".stage-abandoned"
    stage.mkdir()
    (stage / "data").write_bytes(b"abcd")
    result = storage_audit(store)
    by_name = {row["entry"]: row for row in result["items"]}
    assert result["status"] == "inventory_complete"
    assert by_name[scanned[2]]["reference_status"] == "referenced"
    assert by_name[orphan.name]["reference_status"] == "unreferenced"
    assert by_name[orphan.name]["logical_bytes"] == 3
    assert by_name[stage.name]["reference_status"] == "staging"
    assert (stage / "data").read_bytes() == b"abcd"
    output = CliRunner().invoke(app, ["--state-dir", str(store.root), "storage-audit"])
    assert output.exit_code == 0 and json.loads(output.output) == result


def test_limits_links_and_worker_lock(store, scanned, tmp_path):
    limited = storage_audit(store, max_nodes=1)
    assert limited["status"] == "incomplete" and limited["visited_nodes"] <= 1
    assert storage_audit(store, max_entries=1)["status"] == "incomplete"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "sensitive").write_bytes(b"do not measure")
    link = store.root / "scans" / str(uuid4())
    link.symlink_to(outside, target_is_directory=True)
    result = storage_audit(store)
    row = next(item for item in result["items"] if item["entry"] == link.name)
    assert row["logical_bytes"] == 0 and not row["measurement_complete"]
    with exclusive_worker(store.root), pytest.raises(VeriFlowError, match="worker"):
        storage_audit(store)
    with pytest.raises(VeriFlowError, match="Entry limit"):
        storage_audit(store, max_entries=0)


def test_empty_state_and_linked_area(store, tmp_path):
    assert storage_audit(store)["items"] == []
    assert not (store.root / "artifacts").exists()
    (store.root / "codeql").symlink_to(tmp_path, target_is_directory=True)
    result = storage_audit(store)
    assert result["status"] == "incomplete" and result["items"] == []
    assert result["issues"] == [{"area": "codeql", "issue": "area_link_skipped"}]
