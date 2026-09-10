import json

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from traceproof import pipeline
from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.persistence import ScanAttempt
from traceproof.reports import get_report, publish_report, report_history


@pytest.fixture
def query(tmp_path):
    path = tmp_path / "approved.ql"
    path.write_text("// synthetic transport test")
    return path


def test_index_gate_stops_downstream_work(store, scanned, query, monkeypatch):
    monkeypatch.setattr(pipeline, "build_index", lambda *a: {"python_index_gate": "blocked"})

    def forbidden(*args, **kwargs):
        pytest.fail("Downstream stage invoked after blocked index")

    monkeypatch.setattr(pipeline, "extract", forbidden)
    monkeypatch.setattr(pipeline, "analyze", forbidden)
    result = pipeline.scan_run(store, scanned[1], query)
    assert result["status"] == "blocked" and result["report_id"] is None
    assert report_history(store, scanned[0])["reports"] == []


def test_extraction_failure_never_republishes_old_scan(store, scanned, query, monkeypatch):
    old = publish_report(store, scanned[0])
    monkeypatch.setattr(
        pipeline,
        "extract",
        lambda *a, **kw: {"attempt_id": "failed-extraction", "status": "timeout"},
    )
    result = pipeline.scan_run(store, scanned[1], query)
    assert result["stopped_after"] == "extraction" and result["report_id"] is None
    assert result["extraction_id"] == "failed-extraction"
    assert len(report_history(store, scanned[0])["reports"]) == 1
    assert get_report(store, scanned[0], old["report_id"]) == old


def test_exact_attempt_publication_and_cli(store, scanned, query, monkeypatch):
    seen = []

    def extract(*args, **kwargs):
        seen.append(kwargs["timeout"])
        return {"attempt_id": "extraction", "status": "extracted"}

    def analyze(store, extraction_id, query, timeout):
        assert extraction_id == "extraction"
        seen.append(timeout)
        return {"attempt_id": scanned[2], "status": "completed"}

    monkeypatch.setattr(pipeline, "extract", extract)
    monkeypatch.setattr(pipeline, "analyze", analyze)
    result = CliRunner().invoke(
        app,
        [
            "--state-dir",
            str(store.root),
            "scan-run",
            scanned[1],
            str(query),
            "--extraction-timeout",
            "12",
            "--query-timeout",
            "34",
        ],
    )
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert seen == [12, 34] and output["model_calls"] == 0
    assert get_report(store, scanned[0], output["report_id"])["attempt_id"] == scanned[2]


def test_preflight_rejects_bad_query_and_timeout(store, scanned, tmp_path, query):
    with pytest.raises(TraceProofError, match="timeout"):
        pipeline.scan_run(store, scanned[1], query, extraction_timeout=0)
    bad = tmp_path / "bad.py"
    bad.write_text("pass")
    with pytest.raises(TraceProofError, match="trusted local"):
        pipeline.scan_run(store, scanned[1], bad)


def test_failed_query_publishes_incomplete_attempt(store, scanned, query, monkeypatch):
    monkeypatch.setattr(
        pipeline, "extract", lambda *a, **kw: {"attempt_id": "extract", "status": "extracted"}
    )

    def fail_query(*args, **kwargs):
        with store.transaction() as session:
            attempt = session.get(ScanAttempt, scanned[2])
            attempt.report = {**attempt.report, "status": "failed", "execution_complete": False}
        return {"attempt_id": scanned[2], "status": "failed"}

    monkeypatch.setattr(pipeline, "analyze", fail_query)
    result = pipeline.scan_run(store, scanned[1], query)
    assert result["status"] == "incomplete" and result["report_id"]
    assert get_report(store, scanned[0], result["report_id"])["analysis_status"] == "failed"
