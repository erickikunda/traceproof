from pathlib import Path

import pytest

from traceproof.claims import assess_evidence
from traceproof.csharp_parser import parse
from traceproof.models import Decision


def fixture(suite="csharp-core"):
    text = Path(f"tests/fixtures/{suite}/vulnerable/LookupController.cs").read_text()
    snippets = [
        dict(
            id=f"E{i + 1}",
            path="LookupController.cs",
            sha256="pinned",
            snapshot_id="snapshot",
            text=text,
            excerpt_line=1,
            excerpt_end_line=len(text.splitlines()),
            source_line_count=len(text.splitlines()),
            line=line,
            end_line=line,
            flow_id="F0T0",
            flow_step=i,
            flow_steps=2,
        )
        for i, line in enumerate([11, 13])
    ]
    claims = [
        dict(
            obligation=kind,
            evidence_id=eid,
            line=line,
            end_line=line,
            quote=text.splitlines()[line - 1].strip(),
            assessment=assessment,
            explanation="Advisory check",
        )
        for kind, eid, line, assessment in [
            ("source", "E1", 11, "present"),
            ("sink", "E2", 13, "present"),
            ("flow", "E1", 11, "present"),
            ("guard", "E2", 13, "unknown"),
        ]
    ]
    return dict(status="ready", rule_id="cs/sql-injection", snippets=snippets), Decision(
        verdict="needs_review",
        rationale="Review SQL path",
        evidence_ids=["E1", "E2"],
        counterevidence="Guard effectiveness unknown",
        claims=claims,
    )


def test_core_sql_advisory_and_negative_boundary():
    bundle, decision = fixture()
    result = assess_evidence(bundle, decision)
    assert result["passed"] and not result["reachability_proven"]
    assert not assess_evidence(
        bundle, decision.model_copy(update={"verdict": "likely_false_positive"})
    )["passed"]


@pytest.mark.parametrize(
    "change",
    [
        "foreign",
        "shadow",
        "alias",
        "comment",
        "fragment",
        "hash",
        "syntax",
        "conditional",
        "flow",
        "quote",
    ],
)
def test_reject_unsupported_or_inconsistent_evidence(change):
    bundle, decision = fixture()
    for s in bundle["snippets"]:
        if change == "foreign":
            s["text"] = s["text"].replace("Microsoft.AspNetCore.Mvc", "Other.Mvc")
        if change == "shadow":
            s["text"] += "class FromQueryAttribute {}\n"
        if change == "alias":
            s["text"] = "using FromQuery = Other.Attribute;\n" + s["text"]
        if change == "comment":
            s["text"] = s["text"].replace("[FromQuery]", "/*FromQuery*/")
        if change == "fragment":
            s["excerpt_line"] = 2
        if change == "syntax":
            s["text"] = s["text"].replace("public class", "public !!!! class")
        if change == "conditional":
            s["text"] = "#if SOMETHING\n" + s["text"] + "#endif\n"
        if change in ("shadow", "alias", "conditional"):
            s["excerpt_end_line"] = s["source_line_count"] = len(s["text"].splitlines())
    if change == "hash":
        bundle["snippets"][0]["text"] = bundle["snippets"][0]["text"].splitlines(keepends=True)[10]
        bundle["snippets"][0].update(excerpt_line=11, excerpt_end_line=11)
        bundle["snippets"][1]["sha256"] = "other"
    if change == "flow":
        bundle["snippets"][0]["flow_id"] = "other"
    if change == "quote":
        decision = decision.model_copy(
            update={"claims": [c.model_copy(update={"quote": "invented"}) for c in decision.claims]}
        )
    assert not assess_evidence(bundle, decision)["passed"]


def test_parser_limits_and_no_string_anchors():
    assert parse(b"x" * 16385)["status"] == "size_limit"
    assert parse(b"\xff")["status"] == "encoding_error"
    assert not parse(b'class X { string s="[FromQuery] ExecuteReader()"; }')["sources"]


def test_complete_flow_required():
    bundle, decision = fixture()
    for s in bundle["snippets"]:
        s["flow_steps"] = 3
    bundle["snippets"][1]["flow_step"] = 2
    assert not assess_evidence(bundle, decision)["passed"]


def test_parser_failure_and_timeout_fail_closed(monkeypatch):
    import subprocess
    from types import SimpleNamespace

    from traceproof import csharp_claims

    bundle, decision = fixture()
    monkeypatch.setattr(
        csharp_claims.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1)
    )
    assert not assess_evidence(bundle, decision)["passed"]

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("parser", 10)

    monkeypatch.setattr(csharp_claims.subprocess, "run", timeout)
    assert not assess_evidence(bundle, decision)["passed"]


def test_comparison_marks_evidence_policy_change():
    from traceproof.comparison import compatibility

    base = dict(
        language="csharp",
        language_scope={"evidence_gate": "unsupported"},
        candidates=[],
        created_at="2026-09-10",
    )
    current = {**base, "language_scope": {"evidence_gate": "aspnet_sql_review_v2"}}
    assert "evidence_gate:unknown_or_different" in compatibility(base, current)


@pytest.mark.parametrize("suite", ["csharp-core", "csharp-minimal", "csharp-webapi", "csharp-mvc"])
def test_qualified_fixture_parser_sources_and_sql_assignment(suite):
    source = Path(f"tests/fixtures/{suite}/vulnerable/LookupController.cs").read_bytes()
    parsed = parse(source)
    assert parsed["status"] == "parsed"
    assert len(parsed["sources"]) == len(parsed["sinks"]) == 1


@pytest.mark.parametrize("suite", ["csharp", "csharp-classic"])
def test_other_csharp_sources_stay_unqualified(suite):
    source = Path(f"tests/fixtures/{suite}/vulnerable/LookupController.cs").read_bytes()
    assert not parse(source)["sources"]


@pytest.mark.parametrize("suite", ["csharp-webapi", "csharp-mvc"])
@pytest.mark.parametrize(
    "change",
    [
        "private",
        "static",
        "nonaction",
        "foreign",
        "shadow",
        "no_httpget",
        "wrong_base",
        "ambiguous",
    ],
)
def test_classic_action_lookalikes_are_not_sources(suite, change):
    source = Path(f"tests/fixtures/{suite}/vulnerable/LookupController.cs").read_text()
    if change == "private":
        source = source.replace("public DbDataReader", "private DbDataReader")
    if change == "static":
        source = source.replace("public DbDataReader", "public static DbDataReader")
    if change == "nonaction":
        source = source.replace("[HttpGet]", "[HttpGet, NonAction]")
    if change == "foreign":
        source = source.replace("using System.Web.", "using Foreign.")
    if change == "shadow":
        source += "class HttpGetAttribute {}"
    if change == "no_httpget":
        source = source.replace("[HttpGet]", "")
    if change == "wrong_base":
        source = source.replace(": ApiController", ": Unrelated").replace(
            ": Controller", ": Unrelated"
        )
    if change == "ambiguous":
        source = "using Microsoft.AspNetCore.Mvc;\n" + source
    assert not parse(source.encode())["sources"]


@pytest.mark.parametrize("suite", ["csharp-webapi", "csharp-mvc"])
def test_classic_gate_is_advisory_only(suite):
    bundle, decision = fixture(suite)
    gate = assess_evidence(bundle, decision)
    assert gate["passed"] and not gate["reachability_proven"]
    assert not assess_evidence(
        bundle, decision.model_copy(update={"verdict": "likely_false_positive"})
    )["passed"]


@pytest.mark.parametrize(
    "change", ["abstract", "generic_class", "generic_method", "parameter_attribute"]
)
def test_classic_mvc_unsupported_action_shapes(change):
    source = Path("tests/fixtures/csharp-mvc/vulnerable/LookupController.cs").read_text()
    if change == "abstract":
        source = source.replace("public class", "public abstract class")
    if change == "generic_class":
        source = source.replace("class LookupController", "class LookupController<T>")
    if change == "generic_method":
        source = source.replace("Lookup(string", "Lookup<T>(string")
    if change == "parameter_attribute":
        source = source.replace("Lookup(string", "Lookup([Custom] string")
    assert not parse(source.encode())["sources"]
