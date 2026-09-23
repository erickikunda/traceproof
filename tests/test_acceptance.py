import copy
import csv
import io

import pytest
from sqlalchemy import select
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from veriflow.acceptance import FIXTURES, check_case, run_acceptance
from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.indexing import build_index
from veriflow.persistence import Run, ScanAttempt, SourceIndex, exclusive_worker
from veriflow.reports import get_report, publish_report, render_report


def test_missing_then_published_index_changes_report_readiness(store, scanned):
    repo, run, _, _ = scanned
    first = publish_report(store, repo)
    assert first["static_review_readiness"]["state"] == "incomplete"
    assert "current_python_index_missing" in first["static_review_readiness"]["reasons"]
    with exclusive_worker(store.root):
        build_index(store, run)
    second = publish_report(store, repo)
    assert second["static_review_readiness"]["state"] == "ready_for_review"
    assert second["report_version"] == first["report_version"] + 1
    assert not second["coverage_verified"] and second["verified_finding_count"] is None
    assert get_report(store, repo, first["report_id"]) == first
    rows = list(csv.DictReader(io.StringIO(render_report(second, "scan-csv"))))
    assert rows[0]["static_review_readiness"] == "ready_for_review"


def test_blocked_index_not_hidden_by_successful_static_scan(store, evidence_fixture):
    run, _, _, _ = evidence_fixture(source="def broken(:\n")
    with exclusive_worker(store.root):
        build_index(store, run)
    with store.transaction() as session:
        repo = session.get(Run, run).repo_id
    report = publish_report(store, repo)
    assert report["analysis_status"] == "completed"
    assert report["static_review_readiness"]["state"] == "incomplete"
    assert "python_index_blocked" in report["static_review_readiness"]["reasons"]


@pytest.mark.parametrize(
    "change",
    [
        {"status": "failed"},
        {"execution_complete": False},
        {"diagnostic_errors": 1},
        {"unmapped_candidates": 1},
    ],
)
def test_scan_gaps_block_review_readiness(store, scanned, change):
    repo, run, attempt, _ = scanned
    with exclusive_worker(store.root):
        build_index(store, run)
    with store.transaction() as session:
        record = session.get(ScanAttempt, attempt)
        record.report = {**record.report, **change}
    report = publish_report(store, repo)
    assert report["static_review_readiness"]["state"] == "incomplete"


def test_old_parser_index_does_not_satisfy_current_readiness(store, scanned):
    repo, run, _, _ = scanned
    with exclusive_worker(store.root):
        build_index(store, run)
    with store.transaction() as session:
        session.scalar(select(SourceIndex)).version = "old-parser"
    report = publish_report(store, repo)
    assert report["static_review_readiness"]["python_index_gate"] == "unknown"


def test_acceptance_rejects_clean_claim_and_wrong_seed_location():
    report = {
        "report_id": "r",
        "run_id": "run",
        "snapshot_id": "s",
        "security_verdict": "not_adjudicated",
        "verified_finding_count": None,
        "coverage_verified": False,
        "triage_call_count": 0,
        "analysis_status": "completed",
        "execution_complete": True,
        "static_review_readiness": {"state": "ready_for_review"},
        "candidate_count": 1,
        "candidates": [{"rule_id": "py/code-injection", "path": "app.py", "line": 5}],
    }
    assert check_case("vulnerable", report)["passed"]
    changed = copy.deepcopy(report)
    changed["candidates"][0]["line"] = 10
    assert not check_case("vulnerable", changed)["passed"]
    changed = {**report, "candidate_count": 0, "candidates": []}
    assert check_case("fixed", changed)["passed"]
    assert not check_case("fixed", {**changed, "coverage_verified": True})["passed"]
    assert not check_case("fixed", {**changed, "triage_call_count": 1})["passed"]
    with pytest.raises(VeriFlowError, match="Unknown"):
        check_case("other", report)


def test_fixture_contract_and_preserved_output(tmp_path):
    assert "eval(" in FIXTURES["vulnerable"]["app.py"]
    assert "eval(" not in FIXTURES["fixed"]["app.py"]
    assert set(FIXTURES["incomplete"]) == {"app.py", "broken.py"}
    query = tmp_path / "query.ql"
    query.write_text("// test")
    with pytest.raises(VeriFlowError, match="must be new"):
        run_acceptance(tmp_path, query)
    assert query.read_text() == "// test"


def test_legacy_report_formats_show_unknown_readiness(store, scanned):
    report = publish_report(store, scanned[0])
    report.pop("static_review_readiness")
    report["candidates"][0].pop("latest_simulated")
    for format in ("html", "markdown", "scan-csv", "candidates-csv"):
        assert "unknown" in render_report(report, format)


@pytest.mark.parametrize("passed,exit_code", [(True, 0), (False, 1)])
def test_acceptance_cli_failure_is_nonzero(monkeypatch, passed, exit_code):
    monkeypatch.setattr("veriflow.acceptance.run_acceptance", lambda *args: {"passed": passed})
    result = CliRunner().invoke(app, ["acceptance-run", "unused-output", "unused-query.ql"])
    assert result.exit_code == exit_code
    assert '"passed"' in result.output
