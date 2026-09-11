import json
import sys
import zipfile
from uuid import uuid4

import pytest
from conftest import row
from typer.testing import CliRunner

from traceproof.artifacts import ArtifactStore
from traceproof.calls import call_context
from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.evidence import source_evidence
from traceproof.indexing import build_index, coverage_report, verified_source
from traceproof.intake import process, submit
from traceproof.persistence import CodeqlAttempt, ScanAttempt, SourceIndex
from traceproof.sarif import MAX_SARIF_BYTES, normalize
from traceproof.scanning import analyze, scan_report


@pytest.fixture
def captured_source(store, archive, manifest):
    def capture(files):
        with zipfile.ZipFile(archive, "w") as out:
            for name, text in files.items():
                out.writestr(name, text)
        batch = submit(store, manifest([row(archive)]), archive.parent, str(uuid4()))
        run_id = process(store, ArtifactStore(store.root), batch)["items"][0]["run_id"]
        build_index(store, run_id)
        return run_id

    return capture


def test_direct_and_import_candidates(store, captured_source):
    run = captured_source(
        {
            "project/main.py": "from helper import work as w\nimport helper as h\n"
            "def local(): pass\ndef entry():\n local()\n w()\n h.work()\n obj.work()\n",
            "project/helper.py": "def work(): pass\n",
        }
    )
    result = call_context(store, run, "project/main.py", "project")
    assert [call["resolution"] for call in result["items"]] == [
        "static_candidate",
        "static_candidate",
        "static_candidate",
        "unresolved",
    ]
    assert result["items"][1]["candidate"]["path"] == "project/helper.py"
    assert result["reachability_proven"] is False
    assert len(call_context(store, run, "project/main.py", "project", 1, 1)["items"]) == 1
    assert call_context(store, run, "project/main.py")["items"][1]["candidate"] is None


@pytest.mark.parametrize(
    "source",
    [
        "def f(): pass\ndef entry(f): f()",
        "def f(): pass\nf = other\nf()",
        "@decorator\ndef f(): pass\nf()",
        "def f(): pass\nexec('x')\nf()",
        "def f(): pass\nfrom other import *\nf()",
        "def f(): pass\ndef entry():\n global f\n f()",
        "def f(): pass\ntry: pass\nexcept Exception as f: f()",
        "def f(): pass\nmatch x:\n case f: f()",
    ],
)
def test_rebinding_and_dynamic_gaps_remain_unresolved(store, captured_source, source):
    run = captured_source({"app.py": source})
    result = call_context(store, run, "app.py")
    assert all(item["candidate"] is None for item in result["items"])


def test_import_ambiguity(store, captured_source):
    run = captured_source(
        {
            "app.py": "from helper import f\nf()",
            "helper.py": "def f(): pass",
            "helper/__init__.py": "def f(): pass",
        }
    )
    assert call_context(store, run, "app.py")["items"][0]["candidate"] is None


def test_evidence_bounds_encoding_and_tamper(store, captured_source):
    run = captured_source({"app.py": b"# coding: latin1\ndef f():\n return '\xe9'\n"})
    evidence = source_evidence(store, run, "app.py", 2, 3)
    assert "é" in evidence["text"]
    assert evidence["trust"] == "untrusted_source"
    for path, start, end, digest in [
        ("../app.py", 1, 1, None),
        ("app.py", 0, 1, None),
        ("app.py", 1, 201, None),
        ("app.py", 1, 4, None),
        ("app.py", 1, 1, "0" * 64),
    ]:
        with pytest.raises(TraceProofError):
            source_evidence(store, run, path, start, end, digest)
    _, _, tree = verified_source(store, run)
    path = tree / "app.py"
    path.chmod(0o600)
    path.write_text("changed")
    with pytest.raises(TraceProofError):
        source_evidence(store, run, "app.py", 1, 1)


def test_historical_index_selection(store, captured_source):
    run = captured_source({"app.py": "def f(): pass"})
    report = coverage_report(store, run)
    with store.transaction() as session:
        session.get(SourceIndex, report["index_id"]).version = "old-parser"
    assert coverage_report(store, run, report["index_id"]) == report
    with pytest.raises(TraceProofError):
        coverage_report(store, run)


def sarif(uri="app.py", success=True):
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "CodeQL"}},
                "invocations": [{"executionSuccessful": success}],
                "results": [
                    {
                        "ruleId": "py/code-injection",
                        "message": {"text": "untrusted input"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": uri},
                                    "region": {"startLine": 1},
                                }
                            }
                        ],
                    }
                ],
            }
        ],
    }


@pytest.mark.parametrize(
    "uri,mapped",
    [
        ("app.py", True),
        ("%61pp.py", True),
        ("../app.py", False),
        ("https://evil/app.py", False),
        ("file:///tmp/app.py", False),
        ("app.py?x", False),
    ],
)
def test_sarif_location_binding(store, captured_source, uri, mapped):
    run = captured_source({"app.py": "def f(): pass"})
    _, manifest, tree = verified_source(store, run)
    candidates, summary = normalize(json.dumps(sarif(uri)).encode(), manifest, tree)
    assert (candidates[0]["evidence"] is not None) == mapped
    assert candidates[0]["adjudication"] == "unreviewed"
    assert summary["execution_complete"]


def test_sarif_dedupe_diagnostics_and_limits(store, captured_source):
    run = captured_source({"app.py": "def f(): pass"})
    _, manifest, tree = verified_source(store, run)
    doc = sarif(success=False)
    doc["runs"][0]["results"] *= 2
    doc["runs"][0]["invocations"][0]["toolExecutionNotifications"] = [{"level": "error"}]
    candidates, summary = normalize(json.dumps(doc).encode(), manifest, tree)
    assert len(candidates) == 1 and summary["raw_result_count"] == 2
    assert summary["diagnostic_errors"] == 1 and not summary["execution_complete"]
    for raw in [b"{}", b"[]", b"not json", b" " * (MAX_SARIF_BYTES + 1)]:
        with pytest.raises(TraceProofError):
            normalize(raw, manifest, tree)


@pytest.mark.parametrize(
    "mode,status,count",
    [
        ("success", "completed", 1),
        ("empty", "completed", 0),
        ("partial", "partial", 1),
        ("invalid", "invalid_output_or_integrity", None),
        ("failed", "query_failed", None),
        ("timeout", "timeout", None),
    ],
)
def test_query_attempts_durable(store, captured_source, tmp_path, monkeypatch, mode, status, count):
    run = captured_source({"app.py": "def f(): pass"})
    extraction_id = str(uuid4())
    with store.transaction() as session:
        session.add(
            CodeqlAttempt(
                id=extraction_id,
                run_id=run,
                result={
                    "status": "extracted",
                    "run_id": run,
                    "database_path": str(tmp_path / "db"),
                },
            )
        )
    query = tmp_path / "test.ql"
    query.write_text("// operator-controlled fixture")
    fake = tmp_path / "codeql"
    document = sarif(success=mode != "partial")
    if mode == "empty":
        document["runs"][0]["results"] = []
    output = json.dumps(document) if mode != "invalid" else "bad"
    fake.write_text(f"""#!{sys.executable}
import sys, time, os, json
from pathlib import Path
if sys.argv[1] == 'version':
    print(json.dumps({{'version': 'test'}}))
    sys.exit(0)
assert '--no-download' in sys.argv
assert 'TEST_SECRET' not in os.environ
if {mode!r} == 'timeout': time.sleep(30)
path = next(arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--output='))
Path(path).write_text({output!r})
sys.exit(7 if {mode!r} == 'failed' else 0)
""")
    fake.chmod(0o700)
    monkeypatch.setenv("TEST_SECRET", "do-not-forward")
    monkeypatch.setattr("traceproof.codeql_scanner.shutil.which", lambda _: str(fake))
    report = analyze(store, extraction_id, query, timeout=1)
    assert report["status"] == status
    assert report["candidate_count"] == count
    retrieved = scan_report(store, "example")
    assert retrieved["attempt_id"] == report["attempt_id"]
    assert len(retrieved["candidates"]) == (count or 0)
    assert retrieved["verified_finding_count"] is None
    assert retrieved["analysis_codeql_version"] == "test"
    assert retrieved["analysis_identity"]["automatic_reuse_eligible"] is False
    assert len(retrieved["analysis_identity"]["configuration_sha256"]) == 64
    assert retrieved["scanner"]["engine_id"] == "codeql"
    assert retrieved["scanner"]["version"] == "test"
    assert retrieved["scanner"]["capabilities"]["flow_paths_guaranteed"] is False
    assert retrieved["prepared_input"]["preparation_id"] == extraction_id
    assert retrieved["prepared_input"]["snapshot_id"] == retrieved["snapshot_id"]
    assert retrieved["rule_entry"]["sha256"] == retrieved["query_sha256"]
    assert retrieved["rule_entry"]["transitive_dependencies_verified"] is False
    runner = CliRunner()
    result = runner.invoke(
        app, ["--state-dir", str(store.root), "scan-report", "example", "--format", "markdown"]
    )
    assert result.exit_code == 0 and "NOT ADJUDICATED" in result.output
    with store.transaction() as session:
        failed = {**report, "status": "query_failed", "candidate_count": None}
        session.add(ScanAttempt(id=str(uuid4()), run_id=run, created_at="9999", report=failed))
    assert scan_report(store, "example")["status"] == "query_failed"
    assert scan_report(store, "example")["candidates"] == []


def test_evidence_response_budget(store, captured_source):
    run = captured_source({"app.py": "#" + "x" * 33000 + "\ndef f(): pass"})
    with pytest.raises(TraceProofError, match="32 KiB"):
        source_evidence(store, run, "app.py", 1, 1)


def test_sarif_negative_index_and_missing_execution_status(store, captured_source):
    run = captured_source({"app.py": "def f(): pass"})
    _, manifest, tree = verified_source(store, run)
    document = sarif()
    document["runs"][0].pop("invocations")
    _, summary = normalize(json.dumps(document).encode(), manifest, tree)
    assert summary["execution_complete"] is False
    result = document["runs"][0]["results"][0]
    result.pop("ruleId")
    result["ruleIndex"] = -1
    document["runs"][0]["tool"]["driver"]["rules"] = [{"id": "a"}]
    with pytest.raises(TraceProofError):
        normalize(json.dumps(document).encode(), manifest, tree)


def test_evidence_and_call_cli(store, captured_source):
    run = captured_source({"app.py": "def f(): pass\nf()"})
    runner = CliRunner()
    args = ["--state-dir", str(store.root)]
    for command in [["call-context", run, "app.py"], ["source-evidence", run, "app.py", "1", "2"]]:
        result = runner.invoke(app, [*args, *command])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["schema_version"] == "1"
