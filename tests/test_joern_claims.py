import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_slice03 import captured_source as captured_source

from traceproof import joern
from traceproof.bundles import build_bundle
from traceproof.claims import assess_evidence, requirements
from traceproof.joern_claims import RULE, assess_spring_evidence
from traceproof.models import Decision
from traceproof.scanning import scan_report


def review_decision(bundle):
    """Deterministic fixture claims, not generated analysis or a provider response."""
    nodes = [s for s in bundle["snippets"] if s.get("flow_id") == "F0T0"]
    first, last = nodes[0], nodes[-1]
    claims = []
    for kind, node, assessment in [
        ("source", first, "present"),
        ("sink", last, "present"),
        ("flow", first, "present"),
        ("guard", last, "unknown"),
    ]:
        claims.append(
            dict(
                obligation=kind,
                evidence_id=node["id"],
                line=node["line"],
                end_line=node["line"],
                assessment=assessment,
                quote=node["text"].splitlines()[node["line"] - node["excerpt_line"]].strip(),
                explanation="Synthetic source-bound review claim",
            )
        )
    return Decision(
        verdict="needs_review",
        rationale="Review recorded candidate",
        evidence_ids=[first["id"], last["id"]],
        counterevidence="Guards unknown",
        claims=claims,
    )


@pytest.fixture
def audited_bundle(store, captured_source, tmp_path, monkeypatch):
    fixtures = Path(__file__).parent / "fixtures"
    run = captured_source(
        {p.name: p.read_text() for p in (fixtures / "joern-java/vulnerable").glob("*.java")}
    )
    home = tmp_path / "tools"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()

    def fake(command, root, name, timeout):
        if name == "analyze":
            (root / "flows.json").write_bytes(
                (fixtures / "joern-spring-evidence/native-flow.json").read_bytes()
            )

    monkeypatch.setattr(joern, "stage", fake)
    result = joern.discover(store, run, home, language="java")
    report = scan_report(store, "example", run, result["attempt_id"])
    bundle = build_bundle(store, result["attempt_id"], report["candidates"][0]["fingerprint"])
    return bundle


def test_explicit_review_gate_preserves_engine_and_does_not_enable_triage(audited_bundle):
    bundle = audited_bundle
    assert bundle["joern_native_audit"]["status"] == "validated"
    decision = review_decision(bundle)
    result = assess_spring_evidence(bundle, decision)
    assert result["passed"] and result["engine_id"] == "joern"
    assert not result["reachability_proven"] and not result["automatic_triage_enabled"]
    assert not requirements(RULE, "joern")["supported"]
    assert assess_evidence(bundle, decision)["status"] == "unsupported_engine"


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "version",
        "query",
        "sarif",
        "code",
        "order",
        "truncated",
        "context",
        "foreign",
        "negative",
        "quote",
    ],
)
def test_misleading_or_missing_evidence_withheld(audited_bundle, change):
    bundle = deepcopy(audited_bundle)
    decision = review_decision(bundle)
    audit = bundle["joern_native_audit"]
    if change == "missing":
        bundle.pop("joern_native_audit")
    elif change in {"version", "query", "sarif"}:
        audit[
            {"version": "scanner_version", "query": "query_sha256", "sarif": "sarif_sha256"}[change]
        ] = "wrong"
    elif change == "code":
        audit["nodes"][1]["code"] = "fabricated edge"
    elif change == "order":
        audit["nodes"].reverse()
    elif change == "truncated":
        bundle["snippets"].pop()
    elif change == "context":
        for s in bundle["snippets"]:
            s["source_line_count"] += 1
    elif change == "foreign":
        for s in bundle["snippets"]:
            s["text"] = s["text"].replace("org.springframework", "other.springframework")
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
    assert not assess_spring_evidence(bundle, decision)["passed"]


def test_changed_native_file_and_legacy_attempt_cannot_get_validated_audit(store, audited_bundle):
    from traceproof.persistence import ScanAttempt

    b = audited_bundle
    root = store.root / "scans" / b["attempt_id"]
    (root / "flows.json").write_text("{}")
    changed = build_bundle(store, b["attempt_id"], b["candidate_fingerprint"])
    assert changed["joern_native_audit"]["reason"] == "native_integrity"
    with store.transaction() as session:
        attempt = session.get(ScanAttempt, b["attempt_id"])
        attempt.report = {k: v for k, v in attempt.report.items() if k != "native_output_sha256"}
    legacy = build_bundle(store, b["attempt_id"], b["candidate_fingerprint"])
    assert legacy["joern_native_audit"]["status"] == "unavailable"


@pytest.mark.parametrize(
    "policy,expected",
    [
        (None, "unsupported_engine"),
        ("joern-spring-review-v1", "supported_for_review"),
        ("unknown", None),
    ],
)
def test_cli_review_requires_explicit_policy(store, audited_bundle, tmp_path, policy, expected):
    from typer.testing import CliRunner

    from traceproof.cli import app

    path = tmp_path / "decision.json"
    path.write_text(review_decision(audited_bundle).model_dump_json())
    argv = [
        "--state-dir",
        str(store.root),
        "check-evidence",
        audited_bundle["bundle_id"],
        str(path),
    ]
    if policy:
        argv += ["--review-policy", policy]
    result = CliRunner().invoke(app, argv)
    if expected is None:
        assert result.exit_code != 0 and "Unsupported explicit review policy" in result.output
    else:
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["status"] == expected


@pytest.mark.parametrize(
    "change,reason",
    [
        ("coordinate", "native_sarif_mismatch"),
        ("code", "native_code_not_on_source_line"),
        ("query", "unsupported_native_profile"),
    ],
)
def test_native_audit_rechecks_pinned_output_relationships(store, audited_bundle, change, reason):
    import hashlib

    from traceproof.persistence import ScanAttempt

    b = audited_bundle
    path = store.root / "scans" / b["attempt_id"] / "flows.json"
    raw = json.loads(path.read_text())
    if change == "coordinate":
        raw["paths"][0][0]["line"] += 1
    elif change == "code":
        raw["paths"][0][0]["code"] = "not source text"
    path.write_text(json.dumps(raw))
    with store.transaction() as session:
        attempt = session.get(ScanAttempt, b["attempt_id"])
        updated = {
            **attempt.report,
            "native_output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        if change == "query":
            updated["query_sha256"] = "wrong"
        attempt.report = updated
    rebuilt = build_bundle(store, b["attempt_id"], b["candidate_fingerprint"])
    assert rebuilt["joern_native_audit"]["reason"] == reason
