import json

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.history import extraction_history
from veriflow.persistence import CodeqlAttempt


def test_attempt_history_ordering_fields_and_cli(store, scanned):
    repo, run, _, _ = scanned
    records = [
        ("old-undated", {"status": "failed"}),
        ("newer-undated", {"status": "interrupted"}),
        ("dated-1", {"status": "timeout", "created_at": "2026-01-01T00:00:00+00:00"}),
        (
            "dated-2",
            {
                "status": "extracted",
                "created_at": "2026-01-02T00:00:00+00:00",
                "requested_resources": {"threads": 2, "ram_mb": 2048, "secret": "omit"},
                "database_path": "/private/not-for-summary",
                "elapsed_seconds": 5.5,
            },
        ),
    ]
    with store.transaction() as session:
        for identity, result in records:
            session.add(CodeqlAttempt(id=identity, run_id=run, result=result))
    result = extraction_history(store, repo)
    assert result["total"] == 4
    assert [item["attempt_id"] for item in result["items"]] == [
        "dated-2",
        "dated-1",
        "old-undated",
        "newer-undated",
    ]
    assert result["items"][-1]["created_at"] is None
    assert result["items"][0]["elapsed_seconds"] == 5.5
    assert "omit" not in json.dumps(result) and "/private" not in json.dumps(result)
    assert extraction_history(store, repo, run, limit=1)["next_offset"] == 1
    assert extraction_history(store, repo, offset=1)["items"] == result["items"][1:]
    output = CliRunner().invoke(app, ["--state-dir", str(store.root), "extraction-history", repo])
    assert output.exit_code == 0 and json.loads(output.output) == result


def test_scope_empty_and_invalid_page(store, scanned):
    repo, run, _, _ = scanned
    assert extraction_history(store, repo)["items"] == []
    with pytest.raises(VeriFlowError, match="Repository"):
        extraction_history(store, "other", run)
    with pytest.raises(VeriFlowError, match="Run"):
        extraction_history(store, repo, "other")
    with pytest.raises(VeriFlowError, match="pagination"):
        extraction_history(store, repo, limit=0)
