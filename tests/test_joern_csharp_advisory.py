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
from veriflow.joern_claims import CSHARP_POLICY, assess_review_evidence, review_preflight
from veriflow.joern_csharp import PATCHED_SHA256
from veriflow.persistence import ScanAttempt
from veriflow.reports import get_report
from veriflow.scan_advisory import AdvisoryOptions
from veriflow.scanning import scan_report
from veriflow.triage import set_budget, triage


@pytest.fixture(params=["core", "mvc", "webapi"])
def csharp_bundle(request, store, captured_source, tmp_path, monkeypatch):
    path = next(
        (Path(__file__).parent / "fixtures" / f"csharp-{request.param}" / "vulnerable").glob("*.cs")
    )
    source = path.read_text()
    run = captured_source({"Controller.cs": source})
    home = tmp_path / "tools"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()
    monkeypatch.setattr(
        "veriflow.joern_csharp.repaired_frontend",
        lambda *args: (
            ["trusted-tool"],
            {
                "patched_source_sha256": PATCHED_SHA256,
                "receipt_sha256": "a" * 64,
                "publisher_authenticated": False,
            },
        ),
    )
    lines = source.splitlines()
    start = next(i + 1 for i, line in enumerate(lines) if "Lookup(" in line)
    end = next(i + 1 for i, line in enumerate(lines) if ".CommandText =" in line)
    parameter = "[FromQuery] string name" if request.param == "core" else "string name"
    rhs = lines[end - 1].split(" = ")[1].rstrip(";")

    def fake(command, root, stage, timeout):
        if stage == "analyze":
            # Synthetic path with pinned frontend's preceding-line convention.
            (root / "flows.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2",
                        "engine_id": "joern",
                        "rule_id": "veriflow/joern-csharp-lookup-commandtext-v1",
                        "represented_csharp_files": ["Controller.cs"],
                        "source_count": 1,
                        "sink_count": 1,
                        "flow_count": 1,
                        "paths": [
                            [
                                {"file": "Controller.cs", "line": start - 1, "code": parameter},
                                {"file": "Controller.cs", "line": end - 1, "code": "name"},
                                {"file": "Controller.cs", "line": end - 1, "code": rhs},
                            ]
                        ],
                    }
                )
            )

    monkeypatch.setattr(joern, "stage", fake)
    result = joern.discover(store, run, home, repair_dir=tmp_path / "repair")
    report = scan_report(store, "example", run, result["attempt_id"])
    return build_bundle(store, result["attempt_id"], report["candidates"][0]["fingerprint"])


def test_mapped_native_path_and_explicit_policy(csharp_bundle):
    b = csharp_bundle
    gate = assess_review_evidence(b, review_decision(b), CSHARP_POLICY)
    assert gate["passed"], (gate, b["joern_native_audit"])
    assert not gate["reachability_proven"] and not gate["automatic_triage_enabled"]
    assert assess_evidence(b, review_decision(b))["status"] == "unsupported_engine"
    assert not review_preflight(b)["passed"]


@pytest.mark.parametrize("change", ["repair", "span", "context", "code", "quote", "negative"])
def test_incomplete_or_misleading_evidence_withheld(csharp_bundle, change):
    b = deepcopy(csharp_bundle)
    decision = review_decision(b)
    audit = b["joern_native_audit"]
    if change == "repair":
        audit["repair_identity"]["patched_source_sha256"] = "wrong"
    elif change == "span":
        audit["span_version"] = "unknown"
    elif change == "context":
        for s in b["snippets"]:
            s["source_line_count"] += 1
    elif change == "code":
        audit["nodes"][0]["code"] = "unrelated"
    elif change == "quote":
        decision = decision.model_copy(
            update={
                "claims": [
                    decision.claims[0],
                    decision.claims[1].model_copy(update={"quote": audit["nodes"][-1]["code"]}),
                    *decision.claims[2:],
                ]
            }
        )
    else:
        decision = decision.model_copy(update={"verdict": "likely_false_positive"})
    assert not assess_review_evidence(b, decision, CSHARP_POLICY)["passed"]


@pytest.mark.parametrize(
    "change,reason",
    [
        ("native", "native_integrity"),
        ("repair", "unsupported_repair_identity"),
        ("mapping", "source_mapping_mismatch"),
    ],
)
def test_audit_recomputes_mapping_and_requires_repair(store, csharp_bundle, change, reason):
    b = csharp_bundle
    if change == "native":
        (store.root / "scans" / b["attempt_id"] / "flows.json").write_text("{}")
    else:
        with store.transaction() as session:
            attempt = session.get(ScanAttempt, b["attempt_id"])
            report = deepcopy(attempt.report)
            if change == "repair":
                report["repair_identity"] = {}
            else:
                report["source_mapping"]["validated_paths"] += 1
            attempt.report = report
    rebuilt = build_bundle(store, b["attempt_id"], b["candidate_fingerprint"])
    assert rebuilt["joern_native_audit"]["reason"] == reason


@pytest.mark.parametrize("stop", [None, "budget", "evidence"])
def test_cost_and_retry_controls(store, csharp_bundle, monkeypatch, stop):
    b = csharp_bundle
    set_budget(store, b["run_id"], 0 if stop == "budget" else 100000)
    adapter = adapter_for(b)
    if stop == "evidence":
        altered = deepcopy(b)
        altered.pop("joern_native_audit")
        monkeypatch.setattr("veriflow.triage.get_bundle", lambda *args: altered)
    result = triage(store, b["bundle_id"], policy(), adapter, "csharp", review_policy=CSHARP_POLICY)
    assert (
        result["state"]
        == {None: "completed", "budget": "budget_exhausted", "evidence": "incomplete_evidence"}[
            stop
        ]
    )
    assert result["accounted_micro_usd"] == (0 if stop else 140)
    assert not result["verified"]
    assert (
        triage(store, b["bundle_id"], policy(), adapter, "csharp", review_policy=CSHARP_POLICY)
        == result
    )
    assert adapter.calls == (0 if stop else 1)


def test_scan_advisory_and_exact_report(store, csharp_bundle, tmp_path):
    b = csharp_bundle
    set_budget(store, b["run_id"], 100000)
    options = AdvisoryOptions(policy(), adapter_for(b), "csharp-workflow", CSHARP_POLICY)
    result = pipeline.scan_run(
        store,
        b["run_id"],
        engine="joern",
        language="auto",
        joern_home=tmp_path / "tools",
        joern_repair_dir=tmp_path / "repair",
        advisory=options,
    )
    assert result["model_calls"] == 1 and result["live_model_calls"] == 0
    report = get_report(store, b["repo_id"], report_id=result["report_id"])
    assert report["candidates"][0]["latest_advisory"] == "needs_review"
    assert report["static_review_readiness"]["state"] == "incomplete"


def test_mapping_work_is_bounded_before_reparsing(store, csharp_bundle):
    b = csharp_bundle
    path = store.root / "scans" / b["attempt_id"] / "flows.json"
    doc = json.loads(path.read_text())
    doc["paths"] *= 33
    doc["flow_count"] = len(doc["paths"])
    raw = json.dumps(doc).encode()
    path.write_bytes(raw)
    with store.transaction() as session:
        attempt = session.get(ScanAttempt, b["attempt_id"])
        attempt.report = {**attempt.report, "native_output_sha256": hashlib.sha256(raw).hexdigest()}
    rebuilt = build_bundle(store, b["attempt_id"], b["candidate_fingerprint"])
    assert rebuilt["joern_native_audit"]["reason"] == "native_mapping_limit"
