import csv
import io
import json

import pytest
from test_evaluation import evaluation as evaluation
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from traceproof.domain import TraceProofError
from traceproof.evaluation import JOERN_RULES, JoernEvaluationPlan, render_scorecard


def audit_plan(plan, rule="traceproof/joern-python-lookup-system-v1"):
    plan.pop("codeql_version")
    plan.update(
        schema_version="2",
        engine="joern",
        scanner_version="4.0.625",
        mode="discovery_coverage_audit",
        rule_ids=[rule],
    )


def test_audit_does_not_turn_unsupported_coverage_into_recall(evaluation):
    _, _, plan, evaluate = evaluation
    audit_plan(plan)
    report = evaluate()
    assert report["evaluator_version"] == "3"
    assert report["complete"] is False
    assert report["candidate_recall_proxy"]["value"] is None
    assert report["candidate_recall_proxy"]["denominator"] == 1
    row = report["repositories"][0]
    assert "scanner_engine_mismatch_or_unknown" in row["scope_gaps"]
    assert "discovery_profile_not_qualified_for_recall" in row["scope_gaps"]
    assert report["labels"][0]["status"] == "not_evaluable"
    assert all(c["status"] == "unjudged" for c in report["candidates"])
    exported = list(csv.DictReader(io.StringIO(render_scorecard(report, "repositories-csv"))))[0]
    assert "scanner_limitations" in exported and "discovery_coverage" in exported
    summary = list(csv.DictReader(io.StringIO(render_scorecard(report, "summary-csv"))))[0]
    assert summary["candidate_recall_proxy_value"] == ""
    assert "not evaluable (coverage audit)" in render_scorecard(report, "markdown")
    assert "Coverage audit" in render_scorecard(report, "html")


@pytest.mark.parametrize("rule", list(JOERN_RULES))
def test_all_bounded_profiles_have_explicit_audit_scope(evaluation, rule):
    plan = evaluation[2]
    audit_plan(plan, rule)
    assert JoernEvaluationPlan.model_validate(plan).rule_ids == [rule]


def test_unknown_rule_and_cross_engine_plan_rejected(evaluation):
    plan, evaluate = evaluation[2:]
    audit_plan(plan, "py/code-injection")
    with pytest.raises(TraceProofError):
        evaluate()


def test_missing_reports_keep_labels_and_null_metrics(evaluation):
    plan, evaluate = evaluation[2:]
    audit_plan(plan)
    plan["reports"] = []
    report = evaluate()
    assert report["label_count"] == 1
    assert report["repositories"][0]["scope_gaps"] == ["report_not_selected"]
    assert report["weaknesses"][0]["candidate_recall_proxy_value"] is None
    assert json.loads(render_scorecard(report, "json"))["complete"] is False
