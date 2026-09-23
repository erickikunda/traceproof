import json

import pytest
from conftest import row
from typer.testing import CliRunner

from veriflow import batch_scan
from veriflow.artifacts import ArtifactStore
from veriflow.cli import app
from veriflow.domain import TraceProofError
from veriflow.import_controls import control_status, set_control
from veriflow.intake import import_status, process, submit


@pytest.mark.parametrize("pause_first", [False, True])
def test_cancellation_is_terminal_and_idempotent(store, archive, manifest, pause_first):
    batch = submit(store, manifest([row(archive)]), archive.parent, "cancel")
    if pause_first:
        set_control(store, batch, "paused", "pause", "Wait", 0)
    revision = int(pause_first)
    args = [
        "--state-dir",
        str(store.root),
        "import-control",
        batch,
        "cancelled",
        "cancel",
        "No longer needed",
        "--expected-revision",
        str(revision),
    ]
    first = CliRunner().invoke(app, args)
    repeated = CliRunner().invoke(app, args)
    assert first.exit_code == repeated.exit_code == 0
    assert json.loads(first.output) == json.loads(repeated.output)
    for target in ["active", "paused", "cancelled"]:
        with pytest.raises(TraceProofError, match="cannot be resumed"):
            set_control(store, batch, target, "new-key", "Change", revision + 1)
    result = process(store, ArtifactStore(store.root), batch)
    assert result["items"][0]["state"] == "ready" and result["items"][0]["attempts"] == 0
    assert control_status(store, batch)["revision"] == revision + 1
    if pause_first:
        old = set_control(store, batch, "paused", "pause", "Wait", 0)
        assert old["current"]["state"] == "cancelled"


def test_cancellation_during_scan_preserves_completed_row(
    store, archive, manifest, tmp_path, monkeypatch
):
    batch = submit(
        store,
        manifest([row(archive), row(archive, repo_id="second")]),
        archive.parent,
        "cancel-boundary",
    )
    before = process(store, ArtifactStore(store.root), batch)["items"]
    query = tmp_path / "approved.ql"
    query.write_text("// synthetic")
    calls = []

    def scan(*args, **kwargs):
        calls.append(args[1])
        set_control(store, batch, "cancelled", "cancel", "Stop remaining rows", 0)
        return {"status": "ready_for_review", "report_id": "recorded-report"}

    monkeypatch.setattr(batch_scan, "scan_run", scan)
    result = batch_scan.scan_import(store, batch, query, limit=2)
    assert result["dispatch_status"] == "cancelled" and result["next_offset"] is None
    assert len(calls) == 1 and result["items"][0]["report_id"] == "recorded-report"
    assert batch_scan.scan_import(store, batch, query, rescan=True)["items"] == []
    empty = batch_scan.scan_import(store, batch, query, offset=100)
    assert empty["dispatch_status"] == "cancelled" and empty["items"] == []
    assert import_status(store, batch)["items"] == before
