import json
import sqlite3

from typer.testing import CliRunner

from traceproof.cli import app
from traceproof.doctor import diagnose
from traceproof.persistence import Store


def test_missing_state_not_created(tmp_path, monkeypatch):
    monkeypatch.setattr("traceproof.doctor.shutil.which", lambda name: None)
    root = tmp_path / "missing"
    store = Store(root)
    result = diagnose(store)
    store.close()
    assert result["status"] == "blocked" and not root.exists()
    assert {c["check"] for c in result["checks"] if c["status"] == "fail"} == {"database", "codeql"}


def test_schema_and_query_checks(store, tmp_path, monkeypatch):
    monkeypatch.setattr("traceproof.doctor.shutil.which", lambda name: "/approved/codeql")
    query = tmp_path / "query.ql"
    query.write_text("// not compiled by preflight")
    assert diagnose(store, query)["status"] == "preflight_passed"
    assert diagnose(store)["status"] == "incomplete"
    with sqlite3.connect(store.database) as connection:
        connection.execute("UPDATE alembic_version SET version_num='0006'")
    result = diagnose(store, query)
    assert result["status"] == "blocked" and result["recorded_database_schema"] == "0006"
    with sqlite3.connect(store.database) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0006"


def test_bad_database_and_source_query_rejected(store, tmp_path, monkeypatch):
    monkeypatch.setattr("traceproof.doctor.shutil.which", lambda name: "/approved/codeql")
    source = store.root / "artifacts" / "source.ql"
    source.parent.mkdir()
    source.write_text("// untrusted source")
    assert diagnose(store, source)["status"] == "blocked"
    bad_root = tmp_path / "bad"
    bad_root.mkdir()
    (bad_root / "traceproof.db").write_bytes(b"not a sqlite database")
    bad = Store(bad_root)
    assert diagnose(bad)["status"] == "blocked"
    bad.close()


def test_cli_blocked_exit_and_no_credentials_in_output(store, monkeypatch):
    monkeypatch.setattr("traceproof.doctor.shutil.which", lambda name: None)
    monkeypatch.setenv("TRACEPROOF_OPENAI_API_KEY", "synthetic-secret-never-print")
    result = CliRunner().invoke(app, ["--state-dir", str(store.root), "doctor"])
    assert result.exit_code == 1
    assert json.loads(result.output)["status"] == "blocked"
    assert "synthetic-secret-never-print" not in result.output
