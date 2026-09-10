import copy
import hashlib
import json

import pytest
from test_evaluation import evaluation as evaluation
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from traceproof.benchmark_comparison import compare_scorecards, render_comparison
from traceproof.bundles import canonical
from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.persistence import BenchmarkScorecard


@pytest.fixture
def saved(store, evaluation):
    report = evaluation[3]()

    def save(content):
        body = {key: value for key, value in content.items() if key != "scorecard_id"}
        digest = hashlib.sha256(canonical(body)).hexdigest()
        with store.transaction() as session:
            if session.get(BenchmarkScorecard, digest) is None:
                session.add(
                    BenchmarkScorecard(id=digest, dataset_id="test", created_at="1", content=body)
                )
        return digest

    return report, save


def test_match_loss_and_gain_with_disclosed_query_change(store, saved):
    report, save = saved
    baseline = save(report)
    missed = copy.deepcopy(report)
    missed["labels"][0]["status"] = "not_observed"
    missed["candidate_recall_proxy"] = {"numerator": 0, "denominator": 1, "value": 0.0}
    missed["evaluation_scope"]["query_sha256"] = "b" * 64
    current = save(missed)
    result = compare_scorecards(store, "test", baseline, current)
    assert result["status"] == "comparable"
    assert result["matched_label_delta"] == -1 and result["recall_proxy_delta"] == -1
    assert result["transition_counts"] == {"location_match_lost": 1}
    assert "query_sha256" in result["analysis_configuration_changes"]
    reverse = compare_scorecards(store, "test", current, baseline)
    assert reverse["transition_counts"] == {"location_match_gained": 1}
    assert reverse["precision_delta"] is None
    assert "location match lost" in render_comparison(result, "markdown")


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("complete", False, "current_incomplete"),
        ("manifest_sha256", "f" * 64, "manifest_sha256_changed"),
        ("labels_sha256", "f" * 64, "labels_sha256_changed"),
        ("evaluator_version", "999", "evaluator_version_changed"),
    ],
)
def test_incompatible_scorecards_withhold_deltas(store, saved, field, value, reason):
    report, save = saved
    baseline = save(report)
    other = {**report, field: value}
    result = compare_scorecards(store, "test", baseline, save(other))
    assert result["status"] == "not_comparable" and reason in result["reasons"]
    assert result["matched_label_delta"] is None and result["recall_proxy_delta"] is None
    assert result["labels"] == []


def test_same_id_cli_and_wrong_dataset(store, saved):
    report, save = saved
    ident = save(report)
    result = CliRunner().invoke(
        app, ["--state-dir", str(store.root), "benchmark-compare", "test", ident, ident]
    )
    assert result.exit_code == 0, result.output
    comparison = json.loads(result.output)
    assert comparison["matched_label_delta"] == 0
    assert comparison["transition_counts"] == {"unchanged": 1}
    with pytest.raises(TraceProofError, match="belong"):
        compare_scorecards(store, "other", ident, ident)


def test_empty_and_rule_scope_changes_are_not_improvements(store, saved):
    report, save = saved
    baseline = save(report)
    empty = {
        **report,
        "labels": [],
        "candidate_recall_proxy": {"numerator": 0, "denominator": 0, "value": None},
    }
    assert (
        "current_has_no_labels"
        in compare_scorecards(store, "test", baseline, save(empty))["reasons"]
    )
    changed = copy.deepcopy(report)
    changed["evaluation_scope"]["rule_ids"] = ["py/command-line-injection"]
    assert (
        "selected_rules_changed"
        in compare_scorecards(store, "test", baseline, save(changed))["reasons"]
    )
