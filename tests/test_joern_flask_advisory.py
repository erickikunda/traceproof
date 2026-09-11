import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_joern_advisory import adapter_for
from test_joern_claims import review_decision
from test_slice03 import captured_source as captured_source
from test_triage import policy

from traceproof import joern, pipeline
from traceproof.bundles import build_bundle
from traceproof.claims import assess_evidence
from traceproof.domain import TraceProofError
from traceproof.joern_claims import FLASK_POLICY, assess_review_evidence, review_preflight
from traceproof.models import request_body
from traceproof.reports import get_report
from traceproof.scan_advisory import AdvisoryOptions
from traceproof.scanning import scan_report
from traceproof.triage import set_budget, triage


@pytest.fixture
def flask_bundle(store, captured_source, tmp_path, monkeypatch):
    fixtures = Path(__file__).parent / "fixtures"
    run = captured_source({"app.py": (fixtures / "joern-flask/vulnerable/app.py").read_text()})
    home = tmp_path / "tools"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()

    def fake(command, root, name, timeout):
        if name == "analyze":
            (root / "flows.json").write_bytes(
                (fixtures / "joern-flask-advisory/native-flow.json").read_bytes()
            )

    monkeypatch.setattr(joern, "stage", fake)
    result = joern.discover(
        store, run, home, language="python", discovery_profile="python-flask-system-v1"
    )
    report = scan_report(store, "example", run, result["attempt_id"])
    return build_bundle(store, result["attempt_id"], report["candidates"][0]["fingerprint"])


def test_native_intermediate_is_observation_and_explicit_gate_only(flask_bundle):
    b = flask_bundle
    assert b["joern_native_audit"]["status"] == "validated"
    assert not b["joern_native_audit"]["nodes"][1]["source_literal"]
    gate = assess_review_evidence(b, review_decision(b), FLASK_POLICY)
    assert gate["passed"] and not gate["reachability_proven"]
    assert not gate["automatic_triage_enabled"]
    assert assess_evidence(b, review_decision(b))["status"] == "unsupported_engine"
    assert not review_preflight(b)["passed"]


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "query",
        "hash",
        "order",
        "truncated",
        "context",
        "source",
        "sink",
        "literal",
        "negative",
        "quote",
    ],
)
def test_bad_evidence_and_claims_fail_closed(flask_bundle, change):
    b = deepcopy(flask_bundle)
    decision = review_decision(b)
    audit = b["joern_native_audit"]
    if change == "missing":
        b.pop("joern_native_audit")
    elif change == "query":
        audit["query_sha256"] = "wrong"
    elif change == "hash":
        audit["nodes"][0]["sha256"] = "wrong"
    elif change == "order":
        audit["nodes"].reverse()
    elif change == "truncated":
        b["snippets"].pop()
    elif change == "context":
        for s in b["snippets"]:
            s["source_line_count"] += 1
    elif change in {"source", "sink"}:
        # Keep the alternate full context internally hash-consistent to exercise syntax binding.
        old, new = (
            ("from flask", "from other") if change == "source" else ("import os", "import xx")
        )
        for s in b["snippets"]:
            s["text"] = s["text"].replace(old, new)
            s["sha256"] = hashlib.sha256(s["text"].encode()).hexdigest()
        for n in audit["nodes"]:
            n["sha256"] = b["snippets"][0]["sha256"]
    elif change == "literal":
        audit["nodes"][1]["source_literal"] = True
    elif change == "negative":
        decision = decision.model_copy(update={"verdict": "likely_false_positive"})
    else:
        decision = decision.model_copy(
            update={
                "claims": [
                    decision.claims[0].model_copy(update={"quote": "fabricated"}),
                    *decision.claims[1:],
                ]
            }
        )
    assert not assess_review_evidence(b, decision, FLASK_POLICY)["passed"]


def test_sink_argument_alone_does_not_satisfy_call_quote(flask_bundle):
    decision = review_decision(flask_bundle)
    decision = decision.model_copy(
        update={
            "claims": [
                decision.claims[0],
                decision.claims[1].model_copy(update={"quote": "term"}),
                *decision.claims[2:],
            ]
        }
    )
    assert not assess_review_evidence(flask_bundle, decision, FLASK_POLICY)["passed"]


@pytest.mark.parametrize("stop", [None, "budget", "evidence"])
def test_opt_in_cost_gates_and_idempotency(store, flask_bundle, monkeypatch, stop):
    b = flask_bundle
    set_budget(store, b["run_id"], 0 if stop == "budget" else 100000)
    adapter = adapter_for(b)
    if stop == "evidence":
        altered = deepcopy(b)
        altered.pop("joern_native_audit")
        monkeypatch.setattr("traceproof.triage.get_bundle", lambda *args: altered)
    result = triage(store, b["bundle_id"], policy(), adapter, "flask", review_policy=FLASK_POLICY)
    assert (
        result["state"]
        == {None: "completed", "budget": "budget_exhausted", "evidence": "incomplete_evidence"}[
            stop
        ]
    )
    assert adapter.calls == (0 if stop else 1)
    assert not result["verified"]
    assert result["accounted_micro_usd"] == (0 if stop else 140)
    assert (
        triage(store, b["bundle_id"], policy(), adapter, "flask", review_policy=FLASK_POLICY)
        == result
    )
    assert adapter.calls <= 1


def test_main_workflow_and_policy_scope(store, flask_bundle, tmp_path):
    b = flask_bundle
    advisory = AdvisoryOptions(policy(), adapter_for(b), "workflow", FLASK_POLICY)
    with pytest.raises(TraceProofError, match="profile"):
        advisory.validate_scope("python", None)
    with pytest.raises(TraceProofError, match="profile"):
        advisory.validate_scope("java", "python-flask-system-v1")
    set_budget(store, b["run_id"], 100000)
    result = pipeline.scan_run(
        store,
        b["run_id"],
        engine="joern",
        language="auto",
        joern_home=tmp_path / "tools",
        joern_profile="python-flask-system-v1",
        advisory=advisory,
    )
    assert result["model_calls"] == 1 and result["live_model_calls"] == 0
    report = get_report(store, b["repo_id"], report_id=result["report_id"])
    assert report["candidates"][0]["latest_advisory"] == "needs_review"
    assert report["static_review_readiness"]["state"] == "incomplete"


def test_policy_in_provider_request_and_cli(store, flask_bundle, tmp_path):
    from typer.testing import CliRunner

    from traceproof.cli import app

    b = flask_bundle
    body = request_body(b, policy(), review_policy=FLASK_POLICY)
    assert FLASK_POLICY in json.dumps(body)
    decision = tmp_path / "decision.json"
    decision.write_text(review_decision(b).model_dump_json())
    result = CliRunner().invoke(
        app,
        [
            "--state-dir",
            str(store.root),
            "check-evidence",
            b["bundle_id"],
            str(decision),
            "--review-policy",
            FLASK_POLICY,
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["passed"]
