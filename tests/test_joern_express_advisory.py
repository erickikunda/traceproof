import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_joern_advisory import adapter_for
from test_joern_claims import review_decision
from test_slice03 import captured_source as captured_source
from test_triage import policy

from veriflow import joern, pipeline
from veriflow.bundles import build_bundle
from veriflow.claims import assess_evidence
from veriflow.domain import VeriFlowError
from veriflow.joern_claims import RULE_POLICIES, assess_review_evidence, review_preflight
from veriflow.reports import get_report
from veriflow.scan_advisory import AdvisoryOptions
from veriflow.scanning import scan_report
from veriflow.triage import set_budget, triage


@pytest.fixture(params=["javascript", "typescript"])
def express_bundle(request, store, captured_source, tmp_path, monkeypatch):
    language = request.param
    extension = "js" if language == "javascript" else "ts"
    name = f"app.{extension}"
    source = (
        Path(__file__).parent / "fixtures/joern-express" / language / "vulnerable" / name
    ).read_text()
    run = captured_source({name: source})
    home = tmp_path / "tools"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()
    rule = f"veriflow/joern-{language}-express-eval-v1"

    def fake(command, root, stage, timeout):
        if stage == "analyze":
            # Synthetic native contract; the separate Linux runner validates real Joern output.
            (root / "flows.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2",
                        "engine_id": "joern",
                        "rule_id": rule,
                        f"represented_{language}_files": [name],
                        "source_count": 1,
                        "sink_count": 1,
                        "flow_count": 1,
                        "paths": [
                            [
                                {"file": name, "line": 4, "code": "incoming.query.code"},
                                {"file": name, "line": 4, "code": "term"},
                                {"file": name, "line": 5, "code": "term"},
                            ]
                        ],
                    }
                )
            )

    monkeypatch.setattr(joern, "stage", fake)
    result = joern.discover(
        store, run, home, language=language, discovery_profile="express-request-eval-v1"
    )
    report = scan_report(store, "example", run, result["attempt_id"])
    return build_bundle(store, result["attempt_id"], report["candidates"][0]["fingerprint"])


def selected(b):
    return RULE_POLICIES[b["rule_id"]]


def test_explicit_policy_and_source_quotes(express_bundle):
    b = express_bundle
    gate = assess_review_evidence(b, review_decision(b), selected(b))
    assert gate["passed"] and not gate["reachability_proven"]
    assert not gate["automatic_triage_enabled"]
    assert assess_evidence(b, review_decision(b))["status"] == "unsupported_engine"
    assert not review_preflight(b)["passed"]


@pytest.mark.parametrize(
    "change",
    ["missing", "query", "context", "order", "code", "foreign", "shadow", "quote", "negative"],
)
def test_evidence_and_decision_fail_closed(express_bundle, change):
    b = deepcopy(express_bundle)
    decision = review_decision(b)
    audit = b["joern_native_audit"]
    if change == "missing":
        b.pop("joern_native_audit")
    elif change == "query":
        audit["query_sha256"] = "wrong"
    elif change == "order":
        audit["nodes"].reverse()
    elif change == "code":
        audit["nodes"][1]["code"] = "fabricated"
    elif change == "context":
        for s in b["snippets"]:
            s["source_line_count"] += 1
    elif change in {"foreign", "shadow"}:
        for s in b["snippets"]:
            s["text"] = (
                s["text"].replace('from "express"', 'from "foreign"')
                if change == "foreign"
                else s["text"].replace("const term", "const eval = other; const term")
            )
            s["sha256"] = hashlib.sha256(s["text"].encode()).hexdigest()
        for n in audit["nodes"]:
            n["sha256"] = b["snippets"][0]["sha256"]
    elif change == "quote":
        decision = decision.model_copy(
            update={
                "claims": [
                    decision.claims[0],
                    decision.claims[1].model_copy(update={"quote": "term"}),
                    *decision.claims[2:],
                ]
            }
        )
    else:
        decision = decision.model_copy(update={"verdict": "likely_false_positive"})
    assert not assess_review_evidence(b, decision, selected(b))["passed"]


@pytest.mark.parametrize("stop", [None, "budget", "evidence"])
def test_cost_and_idempotency(store, express_bundle, monkeypatch, stop):
    b = express_bundle
    set_budget(store, b["run_id"], 0 if stop == "budget" else 100000)
    adapter = adapter_for(b)
    if stop == "evidence":
        altered = deepcopy(b)
        altered.pop("joern_native_audit")
        monkeypatch.setattr("veriflow.triage.get_bundle", lambda *args: altered)
    result = triage(store, b["bundle_id"], policy(), adapter, "express", review_policy=selected(b))
    assert (
        result["state"]
        == {None: "completed", "budget": "budget_exhausted", "evidence": "incomplete_evidence"}[
            stop
        ]
    )
    assert result["accounted_micro_usd"] == (0 if stop else 140)
    assert not result["verified"]
    assert (
        triage(store, b["bundle_id"], policy(), adapter, "express", review_policy=selected(b))
        == result
    )
    assert adapter.calls == (0 if stop else 1)


def test_main_workflow_and_report(store, express_bundle, tmp_path):
    b = express_bundle
    advisory = AdvisoryOptions(policy(), adapter_for(b), "express-workflow", selected(b))
    with pytest.raises(VeriFlowError, match="profile"):
        advisory.validate_scope("python", None)
    set_budget(store, b["run_id"], 100000)
    result = pipeline.scan_run(
        store,
        b["run_id"],
        engine="joern",
        language="auto",
        joern_home=tmp_path / "tools",
        joern_profile="express-request-eval-v1",
        advisory=advisory,
    )
    assert result["model_calls"] == 1 and result["live_model_calls"] == 0
    report = get_report(store, b["repo_id"], report_id=result["report_id"])
    assert report["candidates"][0]["latest_advisory"] == "needs_review"
    assert report["static_review_readiness"]["state"] == "incomplete"
