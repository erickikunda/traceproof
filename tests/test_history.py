import json

import pytest
from sqlalchemy import event
from typer.testing import CliRunner

from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.history import run_history, scan_history
from veriflow.persistence import Repository, Run, ScanAttempt


@pytest.fixture
def history_store(store):
    with store.transaction() as session:
        session.add_all(
            [
                Repository(id=repo, owner="poc", classification="synthetic")
                for repo in ["demo", "other", "empty"]
            ]
        )
        session.flush()
        session.add_all(
            [
                Run(
                    id=run,
                    repo_id=repo,
                    created_at=date,
                    state="admitted",
                    profile="standard",
                    snapshot_id=None,
                )
                for run, repo, date in [
                    ("old", "demo", "1"),
                    ("new", "demo", "2"),
                    ("foreign", "other", "3"),
                ]
            ]
        )
        session.flush()
        session.add_all(
            [
                ScanAttempt(id=attempt, run_id=run, created_at=date, report=report)
                for attempt, run, date, report in [
                    (
                        "success",
                        "old",
                        "1",
                        {
                            "status": "completed",
                            "candidate_count": 0,
                            "execution_complete": True,
                            "raw_sarif_path": "private/path",
                        },
                    ),
                    ("failed", "old", "2", {"status": "failed", "error": "sensitive text"}),
                    ("foreign-attempt", "foreign", "3", {"status": "completed"}),
                ]
            ]
        )
    return store


def test_history_exposes_unpublished_work_and_preserves_unknowns(history_store):
    history = run_history(history_store, "demo", limit=1)
    assert history["total"] == 2 and history["next_offset"] == 1
    assert history["items"][0]["run_id"] == "new"
    assert history["items"][0]["latest_attempt_id"] is None
    older = run_history(history_store, "demo", offset=1, limit=1)
    assert older["next_offset"] is None
    assert older["items"][0]["latest_attempt_id"] == "failed"
    scans = scan_history(history_store, "demo")
    assert [row["attempt_id"] for row in scans["items"]] == ["failed", "success"]
    assert scans["items"][0]["candidate_count"] is None
    assert scans["items"][0]["execution_complete"] is None
    assert scans["items"][1]["candidate_count"] == 0
    assert "sensitive" not in json.dumps(scans) and "private/path" not in json.dumps(scans)
    assert scan_history(history_store, "demo", run_id="new")["total"] == 0
    assert scan_history(history_store, "demo", limit=1)["next_offset"] == 1


def test_scope_and_empty_pages(history_store):
    assert run_history(history_store, "empty")["items"] == []
    assert scan_history(history_store, "demo", offset=99)["items"] == []
    with pytest.raises(VeriFlowError, match="Repository not found"):
        run_history(history_store, "missing")
    for run in ["foreign", "missing"]:
        with pytest.raises(VeriFlowError, match="belong"):
            scan_history(history_store, "demo", run_id=run)


@pytest.mark.parametrize("offset,limit", [(-1, 100), (0, 0), (0, 1001), (True, 100)])
def test_invalid_pagination(history_store, offset, limit):
    for operation in [run_history, scan_history]:
        with pytest.raises(VeriFlowError, match="pagination"):
            operation(history_store, "demo", offset=offset, limit=limit)


def test_read_only_and_cli_contract(history_store):
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.strip().split()[0].upper())

    event.listen(history_store.engine, "before_cursor_execute", capture)
    run_history(history_store, "demo")
    scan_history(history_store, "demo")
    assert not {"INSERT", "UPDATE", "DELETE", "CREATE"} & set(statements)
    for command in ["run-history", "scan-history"]:
        result = CliRunner().invoke(
            app, ["--state-dir", str(history_store.root), command, "demo", "--limit", "1"]
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["next_offset"] == 1
