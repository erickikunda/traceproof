import copy
import hashlib
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
from traceproof.evaluation import evaluate_benchmark, render_scorecard
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
