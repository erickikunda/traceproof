import json

import pytest
from conftest import row
from typer.testing import CliRunner

from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.import_controls import set_control
from traceproof.import_history import import_history
from traceproof.intake import submit
from traceproof.persistence import ImportBatch


def test_states_counts_filtering_and_ties(store, archive, manifest):
    batches = [
        submit(
            store,
            manifest([row(archive), row(archive, repo_id="bad", source_type="gcs")]),
            archive.parent,
            f"private-key-{i}",
        )
        for i in range(3)
    ]
    with store.transaction() as session:
        for identity in batches:
            session.get(ImportBatch, identity).created_at = "same-time"
    set_control(store, batches[1], "paused", "pause", "Private reason", 0)
    set_control(store, batches[2], "paused", "pause", "Wait", 0)
    set_control(store, batches[2], "active", "resume", "Ready", 1)
    set_control(store, batches[2], "cancelled", "cancel", "Done", 2)
    result = import_history(store)
    assert [item["import_id"] for item in result["items"]] == sorted(batches, reverse=True)
    assert result["total"] == 3 and result["next_offset"] is None
    for state, identity in zip(["active", "paused", "cancelled"], batches, strict=True):
        selected = import_history(store, state=state)
        assert selected["total"] == 1 and selected["items"][0]["import_id"] == identity
        assert selected["items"][0]["intake_counts"] == {"ready": 1, "rejected": 1}
        assert selected["items"][0]["total_rows"] == 2
    assert import_history(store, state="cancelled")["items"][0]["control_revision"] == 3
    first = import_history(store, limit=1)
    assert first["next_offset"] == 1
    assert import_history(store, offset=1, limit=2)["items"] == result["items"][1:]
    serialized = json.dumps(result)
    assert "private-key" not in serialized and str(archive.parent) not in serialized
    assert "Private reason" not in serialized


def test_empty_invalid_and_cli(store):
    assert import_history(store)["items"] == []
    assert import_history(store, offset=100)["next_offset"] is None
    with pytest.raises(TraceProofError, match="Dispatch state"):
        import_history(store, state="failed")
    with pytest.raises(TraceProofError, match="pagination"):
        import_history(store, limit=0)
    result = CliRunner().invoke(
        app, ["--state-dir", str(store.root), "import-history", "--state", "paused", "--limit", "5"]
    )
    assert result.exit_code == 0 and json.loads(result.output)["state_filter"] == "paused"
