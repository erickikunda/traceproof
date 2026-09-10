from copy import deepcopy
from pathlib import Path

from traceproof.claims import assess_evidence
from traceproof.models import Decision


def fixture():
    text = (Path(__file__).parent / "fixtures/spring/vulnerable/LookupController.java").read_text()
    snippets = [
        dict(
            id=f"E{i + 1}",
            path="LookupController.java",
            sha256="pinned",
            text=text,
            excerpt_line=1,
            excerpt_end_line=15,
            source_line_count=15,
            line=line,
            end_line=line,
            flow_id="F0T0",
            flow_step=i,
            flow_steps=2,
        )
        for i, line in enumerate([12, 13])
    ]
    claims = [
        dict(
            obligation=kind,
            evidence_id=eid,
            line=line,
            end_line=line,
            quote=text.splitlines()[line - 1].strip(),
            assessment=assessment,
            explanation="Synthetic advisory evidence",
        )
        for kind, eid, line, assessment in [
            ("source", "E1", 12, "present"),
            ("sink", "E2", 13, "present"),
            ("flow", "E1", 12, "present"),
            ("guard", "E2", 13, "unknown"),
        ]
    ]
    return dict(status="ready", rule_id="java/sql-injection", snippets=snippets), Decision(
        verdict="needs_review",
        rationale="Review retained path",
        evidence_ids=["E1", "E2"],
        counterevidence="Guard effectiveness unknown",
        claims=claims,
    )


def test_java_sql_requires_real_syntax_and_retained_path():
    bundle, decision = fixture()
    result = assess_evidence(bundle, decision)
    assert result["passed"] and not result["reachability_proven"]


def test_foreign_import_local_shadow_or_missing_file_context_rejects():
    bundle, decision = fixture()
    for change in ["foreign", "shadow", "fragment", "comment"]:
        altered = deepcopy(bundle)
        for s in altered["snippets"]:
            if change == "foreign":
                s["text"] = s["text"].replace(
                    "org.springframework.web.bind.annotation.RequestParam", "other.RequestParam"
                )
            elif change == "shadow":
                s["text"] += "@interface RequestParam {}\n"
                s["excerpt_end_line"] = s["source_line_count"] = 16
            elif change == "fragment":
                s["excerpt_line"] = 2
            else:
                s["text"] = s["text"].replace(
                    "@RequestParam String name", "/* @RequestParam */ String name"
                )
        assert not assess_evidence(altered, decision)["passed"]


def test_java_missing_flow_and_negative_advice_rejected():
    bundle, decision = fixture()
    bundle["snippets"][0]["flow_id"] = "other"
    assert not assess_evidence(bundle, decision)["passed"]
    bundle, decision = fixture()
    assert not assess_evidence(
        bundle, decision.model_copy(update={"verdict": "likely_false_positive"})
    )["passed"]
