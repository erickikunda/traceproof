import copy
import csv
import hashlib
import io
import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from traceproof.bundles import canonical
from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.evaluation import evaluate_benchmark, render_scorecard, weakness_metrics
from traceproof.indexing import build_index
from traceproof.persistence import (
    Candidate,
    Run,
    ScanAttempt,
    Snapshot,
    TriageCall,
    exclusive_worker,
)
from traceproof.reports import publish_report


def csv_rows(report, format):
    return list(csv.DictReader(io.StringIO(render_scorecard(report, format))))


def test_weakness_partition_preserves_gaps_and_no_label_classes():
    rows = [
        {"cwe": "CWE-94", "status": status}
        for status in ["matched_location", "not_observed", "ambiguous", "not_evaluable"]
    ] + [{"cwe": "CWE-999", "status": "not_evaluable"}]
    metrics = weakness_metrics(rows, {"CWE-94", "CWE-78"}, {"CWE-22"})
    by_cwe = {row["cwe"]: row for row in metrics}
    assert sum(row["label_count"] for row in metrics) == 5
    assert sum(row["candidate_recall_proxy_numerator"] for row in metrics) == 1
    assert by_cwe["CWE-94"]["candidate_recall_proxy_value"] == 0.25
    assert by_cwe["CWE-94"]["status"] == "incomplete"
    assert by_cwe["CWE-999"]["selected_rule_scope"] is False
    for cwe in ["CWE-78", "CWE-22"]:
        assert by_cwe[cwe]["status"] == "no_labels"
        assert by_cwe[cwe]["candidate_recall_proxy_value"] is None


def test_weakness_formats_and_reconciliation(evaluation):
    report = evaluation[3]()
    assert report["evaluator_version"] == "2"
    metric = report["weaknesses"][0]
    assert (
        metric["candidate_recall_proxy_numerator"] == report["candidate_recall_proxy"]["numerator"]
    )
    assert metric["candidate_recall_proxy_denominator"] == report["label_count"]
    row = csv_rows(report, "weaknesses-csv")[0]
    assert row["cwe"] == "CWE-94" and row["scorecard_id"] == report["scorecard_id"]
    assert row["precision"] == row["confirmed_recall"] == ""
    assert "Results by weakness class" in render_scorecard(report, "markdown")
    evaluation[2]["reports"] = []
    missing = evaluation[3]()["weaknesses"][0]
    assert missing["candidate_recall_proxy_denominator"] == 1
    assert missing["status"] == "incomplete"


def test_legacy_scorecard_rendering_does_not_invent_metrics(evaluation):
    report = evaluation[3]()
    del report["weaknesses"]
    report["evaluator_version"] = "1"
    assert "Results by weakness class" not in render_scorecard(report, "markdown")
    assert csv_rows(report, "summary-csv")
    with pytest.raises(TraceProofError, match="legacy"):
        render_scorecard(report, "weaknesses-csv")


def test_csv_grains_reconcile_and_preserve_scorecard(evaluation):
    report = evaluation[3]()
    before = copy.deepcopy(report)
    summary = csv_rows(report, "summary-csv")[0]
    assert summary["candidate_recall_proxy_numerator"] == "1"
    assert summary["candidate_recall_proxy_denominator"] == "1"
    assert summary["precision"] == summary["confirmed_recall"] == ""
    assert json.loads(summary["evaluation_scope"]) == report["evaluation_scope"]
    for grain in ["repositories", "labels", "candidates"]:
        rows = csv_rows(report, grain + "-csv")
        assert len(rows) == len(report[grain])
        assert all(row["scorecard_id"] == report["scorecard_id"] for row in rows)
        assert all(row["plan_sha256"] == report["plan_sha256"] for row in rows)
        assert all(row["grain"] == grain for row in rows)
    assert report == before == evaluation[3]()


def test_csv_missing_scan_has_blank_count_and_explicit_label(evaluation):
    evaluation[2]["reports"] = []
    report = evaluation[3]()
    repo = csv_rows(report, "repositories-csv")[0]
    assert repo["candidate_count"] == "" and repo["report_id"] == ""
    assert json.loads(repo["scope_gaps"]) == ["report_not_selected"]
    assert csv_rows(report, "labels-csv")[0]["status"] == "not_evaluable"
    assert csv_rows(report, "summary-csv")[0]["candidate_recall_proxy_denominator"] == "1"
    assert csv_rows(report, "candidates-csv") == []
    assert "scorecard_id" in render_scorecard(report, "candidates-csv").splitlines()[0]


def test_csv_escaping_and_zero_denominator(evaluation):
    report = evaluation[3]()
    report["repositories"][0]["repo_id"] = " =FORMULA(),\nvalue"
    assert csv_rows(report, "repositories-csv")[0]["repo_id"] == "' =FORMULA(),\nvalue"
    evaluation[1]["labels"] = []
    empty = evaluation[3]()
    summary = csv_rows(empty, "summary-csv")[0]
    assert summary["candidate_recall_proxy_denominator"] == "0"
    assert summary["candidate_recall_proxy_value"] == ""
    assert csv_rows(empty, "candidates-csv")[0]["status"] == "unjudged"


def test_csv_cli(evaluation, store, tmp_path):
    evaluation[3]()
    result = CliRunner().invoke(
        app,
        [
            "--state-dir",
            str(store.root),
            "benchmark-evaluate",
            str(tmp_path / "manifest.json"),
            str(tmp_path / "labels.json"),
            str(tmp_path / "plan.json"),
            "--format",
            "summary-csv",
        ],
    )
    assert result.exit_code == 0, result.output
    assert list(csv.DictReader(io.StringIO(result.output)))[0]["repository_count"] == "1"


@pytest.fixture
def evaluation(store, scanned, tmp_path):
    repo, run, attempt, _ = scanned
    with exclusive_worker(store.root):
        build_index(store, run)
    with store.transaction() as session:
        snapshot = session.get(Snapshot, session.get(Run, run).snapshot_id)
        record = session.get(ScanAttempt, attempt)
        record.report = {
            **record.report,
            "query_sha256": "a" * 64,
            "analysis_codeql_version": "2.27.0",
        }
    manifest = {
        "schema_version": "1",
        "dataset_id": "test",
        "dataset_version": "v1",
        "repositories": [
            {
                "repo_id": repo,
                "snapshot_id": snapshot.id,
                "languages": ["python"],
                "weakness_scope": ["CWE-94"],
                "label_coverage": "known_positives_only",
            }
        ],
    }
    digest = hashlib.sha256(canonical(manifest)).hexdigest()
    labels = {
        "schema_version": "1",
        "dataset_id": "test",
        "label_set_version": "v1",
        "manifest_sha256": digest,
        "labels": [
            {
                "label_id": "label",
                "repo_id": repo,
                "snapshot_id": snapshot.id,
                "root_cause_id": "cause",
                "cwe": "CWE-94",
                "path": "app.py",
                "file_sha256": snapshot.manifest["files"][0]["sha256"],
                "line": 2,
                "end_line": 2,
                "symbol": "f",
                "adjudication_reference": "synthetic",
            }
        ],
    }
    plan = {
        "schema_version": "1",
        "manifest_sha256": digest,
        "query_sha256": "a" * 64,
        "codeql_version": "2.27.0",
        "profile": "standard",
        "rule_ids": ["py/code-injection"],
        "reports": [{"repo_id": repo, "report_id": publish_report(store, repo)["report_id"]}],
    }

    def execute():
        paths = []
        for name, value in (("manifest", manifest), ("labels", labels), ("plan", plan)):
            path = tmp_path / f"{name}.json"
            path.write_text(json.dumps(value))
            paths.append(path)
        return evaluate_benchmark(store, *paths)

    return manifest, labels, plan, execute


def test_unique_location_match_is_provisional_and_read_only(store, evaluation):
    result = evaluation[3]()
    assert result == evaluation[3]()
    assert result["candidate_recall_proxy"] == {"numerator": 1, "denominator": 1, "value": 1.0}
    assert result["precision"] is None and result["confirmed_recall"] is None
    assert result["complete"] and result["labels"][0]["status"] == "matched_location"
    with store.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Run)) == 1
        assert session.scalar(select(func.count()).select_from(TriageCall)) == 0


def test_missing_report_stays_in_denominator(evaluation):
    _, _, plan, execute = evaluation
    plan["reports"] = []
    result = execute()
    assert result["candidate_recall_proxy"]["denominator"] == 1
    assert result["candidate_recall_proxy"]["numerator"] == 0
    assert result["label_counts"]["not_evaluable"] == 1 and not result["complete"]
    assert len(result["repositories"]) == 1


@pytest.mark.parametrize("field,value", [("query_sha256", "b" * 64), ("codeql_version", "2.28.0")])
def test_config_mismatch_not_counted_as_miss(evaluation, field, value):
    _, _, plan, execute = evaluation
    plan[field] = value
    result = execute()
    assert result["label_counts"]["not_observed"] == 0
    assert result["label_counts"]["not_evaluable"] == 1


def test_wrong_label_file_digest_is_unevaluable(evaluation):
    _, labels, _, execute = evaluation
    labels["labels"][0]["file_sha256"] = "f" * 64
    result = execute()
    assert result["label_counts"]["not_evaluable"] == 1
    assert result["repositories"][0]["status"] == "partial"


def test_unmatched_prediction_remains_unjudged(evaluation):
    _, labels, _, execute = evaluation
    labels["labels"][0].update(line=10, end_line=10)
    result = execute()
    assert result["label_counts"]["not_observed"] == 1
    assert result["candidate_counts"]["unjudged"] == 1
    assert result["precision"] is None


def test_one_prediction_cannot_match_two_labels(evaluation):
    _, labels, _, execute = evaluation
    labels["labels"].append(
        {**labels["labels"][0], "label_id": "second", "root_cause_id": "second"}
    )
    result = execute()
    assert result["label_counts"]["ambiguous"] == 2
    assert result["candidate_counts"]["ambiguous"] == 1
    assert result["candidate_recall_proxy"]["numerator"] == 0 and not result["complete"]


def test_two_predictions_do_not_inflate_label_matches(store, scanned, evaluation):
    repo, _, attempt, _ = scanned
    with store.transaction() as session:
        original = session.scalar(select(Candidate).where(Candidate.attempt_id == attempt))
        session.add(
            Candidate(
                id=str(uuid4()),
                attempt_id=attempt,
                fingerprint="c" * 64,
                evidence=copy.deepcopy(original.evidence),
            )
        )
        record = session.get(ScanAttempt, attempt)
        record.report = {**record.report, "candidate_count": 2}
    evaluation[2]["reports"][0]["report_id"] = publish_report(store, repo)["report_id"]
    result = evaluation[3]()
    assert result["label_counts"]["ambiguous"] == 1
    assert result["candidate_counts"]["ambiguous"] == 2


def test_failed_report_does_not_become_false_negative(store, scanned, evaluation):
    with store.transaction() as session:
        record = session.get(ScanAttempt, scanned[2])
        record.report = {**record.report, "status": "failed", "execution_complete": False}
    evaluation[2]["reports"][0]["report_id"] = publish_report(store, scanned[0])["report_id"]
    result = evaluation[3]()
    assert result["label_counts"]["not_evaluable"] == 1
    assert result["candidate_recall_proxy"]["denominator"] == 1


def test_empty_labels_have_null_proxy(evaluation):
    evaluation[1]["labels"] = []
    result = evaluation[3]()
    assert result["candidate_recall_proxy"]["value"] is None
    assert result["candidate_counts"]["unjudged"] == 1


def test_plan_pin_and_duplicates_rejected(evaluation):
    _, _, plan, execute = evaluation
    plan["manifest_sha256"] = "e" * 64
    with pytest.raises(TraceProofError, match="manifest"):
        execute()
    plan["reports"].append(copy.deepcopy(plan["reports"][0]))
    with pytest.raises(TraceProofError, match="Invalid"):
        execute()


def test_bounded_matching(evaluation, monkeypatch):
    monkeypatch.setattr("traceproof.evaluation.MAX_PAIR_CHECKS", 0)
    with pytest.raises(TraceProofError, match="bounded"):
        evaluation[3]()


def test_cli_and_markdown(store, evaluation, tmp_path):
    report = evaluation[3]()
    assert report["scorecard_id"] in render_scorecard(report, "markdown")
    args = ["--state-dir", str(store.root), "benchmark-evaluate"]
    args += [str(tmp_path / f"{name}.json") for name in ("manifest", "labels", "plan")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0 and report["scorecard_id"] in result.output
