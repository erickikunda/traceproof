import json
import subprocess
import sys
import zipfile

import pytest
from conftest import row
from sqlalchemy import func, select
from typer.testing import CliRunner

from veriflow import indexing
from veriflow.artifacts import ArtifactStore
from veriflow.cli import app
from veriflow.codeql import extract, extraction_status
from veriflow.domain import VeriFlowError
from veriflow.intake import process, run_status, submit
from veriflow.persistence import IndexedFile, SourceIndex, exclusive_worker
from veriflow.python_parser import MAX_BYTES, parse


def captured(store, archive, manifest):
    batch = submit(store, manifest([row(archive)]), archive.parent, "index-test")
    with exclusive_worker(store.root):
        return process(store, ArtifactStore(store.root), batch)["items"][0]["run_id"]


def test_inventory_scopes_and_unresolved_calls():
    result = parse(b"""@decorate()
async def outer(x=default()):
    def inner():
        return x.method()
    return inner()
class Example(base()):
    def method(self):
        return factory()()
""")
    assert result["status"] == "parsed"
    assert [s["name"] for s in result["symbols"]] == [
        "outer",
        "outer.inner",
        "Example",
        "Example.method",
    ]
    assert result["symbols"][0]["async"]
    assert {(c["expression"], c["caller"]) for c in result["calls"]} >= {
        ("decorate", "<module>"),
        ("default", "<module>"),
        ("base", "<module>"),
        ("x.method", "outer.inner"),
        ("inner", "outer"),
        ("<dynamic>", "Example.method"),
    }
    assert all(c["resolution"] == "unresolved" for c in result["calls"])


@pytest.mark.parametrize(
    "source,status",
    [
        (b"def broken(:", "parse_error"),
        (b"\xff", "parse_error"),
        (b"x" * (MAX_BYTES + 1), "size_limit"),
        (b"x=1\n" * 15000, "node_limit"),
        (b"# coding: latin1\nx='\xe9'\n", "parsed"),
    ],
)
def test_parser_gaps(source, status):
    assert parse(source)["status"] == status


def test_index_report_query_and_reuse(store, archive, manifest, monkeypatch):
    run_id = captured(store, archive, manifest)
    report = indexing.build_index(store, run_id)
    assert report["python_index_gate"] == "ready"
    assert report["parsed_python_files"] == 1
    assert report["finding_count"] is None
    assert report["security_verdict"] == "not_assessed"
    assert indexing.repository_report(store, "example") == report
    item = indexing.query_index(store, run_id)["items"][0]
    assert item["name"] == "greet"
    assert item["evidence"]["snapshot_id"] == report["snapshot_id"]
    assert item["evidence"]["end_line"] == 2
    assert indexing.query_index(store, run_id, offset=1)["items"] == []
    monkeypatch.setattr(indexing, "parse_isolated", lambda _: pytest.fail("reparsed"))
    assert indexing.build_index(store, run_id) == report
    assert run_status(store, run_id)["coverage_report_status"] == "available"
    with store.transaction() as session:
        assert session.scalar(select(func.count()).select_from(SourceIndex)) == 1


@pytest.mark.parametrize(
    "files",
    [
        {"app.py": "def broken(:"},
        {"app.py": "x = 1"},
        {"app.js": "f()"},
        {"ok.py": "def f(): pass", "bad.py": "def broken(:"},
    ],
)
def test_incomplete_or_empty_gate_blocked(store, archive, manifest, files):
    with zipfile.ZipFile(archive, "w") as out:
        for path, source in files.items():
            out.writestr(path, source)
    report = indexing.build_index(store, captured(store, archive, manifest))
    assert report["python_index_gate"] == "blocked"
    assert not report["security_analysis_performed"]


def test_process_death_checkpoint_resumes_without_partial_publication(store, archive, manifest):
    run_id = captured(store, archive, manifest)
    program = """
import os, sys
from pathlib import Path
from veriflow import indexing
from veriflow.persistence import Store, exclusive_worker
store = Store(Path(sys.argv[1]))
indexing.parse_isolated = lambda _: os._exit(42)
with exclusive_worker(store.root):
    indexing.build_index(store, sys.argv[2])
"""
    child = subprocess.run([sys.executable, "-c", program, str(store.root), run_id], timeout=20)
    assert child.returncode == 42
    with store.transaction() as session:
        assert session.scalar(select(func.count()).select_from(IndexedFile)) == 1
    with pytest.raises(VeriFlowError, match="No published"):
        indexing.coverage_report(store, run_id)
    report = indexing.build_index(store, run_id)
    assert report["python_index_gate"] == "ready"
    with store.transaction() as session:
        assert session.scalar(select(func.count()).select_from(IndexedFile)) == 2


def test_integrity_and_latest_report_do_not_fallback(store, archive, manifest):
    run_id = captured(store, archive, manifest)
    report = indexing.build_index(store, run_id)
    submit(store, manifest([row(archive)]), archive.parent, "new-run")
    with pytest.raises(VeriFlowError, match="no captured"):
        indexing.repository_report(store, "example")
    assert indexing.repository_report(store, "example", run_id) == report
    path = ArtifactStore(store.root).path(report["snapshot_id"]) / "tree/project/app.py"
    path.chmod(0o600)
    path.write_text("changed")
    with pytest.raises(VeriFlowError):
        indexing.build_index(store, run_id)
    # Read-only materialized historical report requires no source reads.
    assert indexing.coverage_report(store, run_id) == report


def test_source_is_not_executed(store, archive, manifest, tmp_path):
    marker = tmp_path / "executed"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("app.py", f"open({str(marker)!r}, 'w').write('bad')\ndef f(): pass")
    indexing.build_index(store, captured(store, archive, manifest))
    assert not marker.exists()


def test_codeql_unavailable_is_durable(store, archive, manifest, monkeypatch):
    run_id = captured(store, archive, manifest)
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: None)
    result = extract(store, run_id)
    assert result["status"] == "unavailable"
    assert not result["security_analysis_performed"]
    assert extraction_status(store, result["attempt_id"]) == result


def test_cli_index_and_reports(store, archive, manifest):
    run_id = captured(store, archive, manifest)
    runner = CliRunner()
    args = ["--state-dir", str(store.root)]
    for command in [["index-run", run_id], ["query-index", run_id], ["repo-report", "example"]]:
        result = runner.invoke(app, [*args, *command])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["schema_version"] == "1"
    result = runner.invoke(app, [*args, "repo-report", "example", "--format", "markdown"])
    assert result.exit_code == 0 and "NOT ASSESSED" in result.output


@pytest.mark.parametrize(
    "mode,expected", [("success", "extracted"), ("failure", "failed"), ("timeout", "timeout")]
)
def test_codeql_process_outcomes(store, archive, manifest, monkeypatch, tmp_path, mode, expected):
    run_id = captured(store, archive, manifest)
    executable = tmp_path / "fake-codeql"
    executable.write_text(f"""#!{sys.executable}
import json, os, sys, time
if sys.argv[1] == 'version':
    print(json.dumps({{'version': 'test'}}))
    sys.exit(0)
assert 'TEST_SECRET' not in os.environ
assert '--build-mode=none' in sys.argv
assert '--language=python' in sys.argv
assert not any(arg.startswith('--command') for arg in sys.argv)
if {mode!r} == 'timeout': time.sleep(30)
sys.exit(7 if {mode!r} == 'failure' else 0)
""")
    executable.chmod(0o700)
    monkeypatch.setenv("TEST_SECRET", "never-pass-to-extractor")
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: str(executable))
    result = extract(store, run_id, timeout=1)
    assert result["status"] == expected
    assert result["codeql_version"] == "test"
    assert result["coverage_verified"] is False
    assert extraction_status(store, result["attempt_id"]) == result


def test_migrate_existing_intake_database(store, archive, manifest):
    from importlib.resources import files

    from alembic import command
    from alembic.config import Config

    # Seed intake data with the current application before recreating the old schema.
    run_id = captured(store, archive, manifest)
    config = Config()
    config.set_main_option("script_location", str(files("veriflow") / "migrations"))
    with store.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0001")
    store.initialize()
    assert indexing.build_index(store, run_id)["python_index_gate"] == "ready"


def test_subprocess_timeout_becomes_coverage_gap(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("parser", 10)

    monkeypatch.setattr(indexing.subprocess, "run", timeout)
    assert indexing.parse_isolated(b"x = 1")["status"] == "timeout"
