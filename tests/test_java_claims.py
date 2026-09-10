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


def expanded_fixture():
    bundle, decision = fixture()
    source = bundle["snippets"][0]["text"] + "// retained context\n" * 45
    lines = source.splitlines(keepends=True)
    for snippet in bundle["snippets"]:
        snippet.update(
            text="".join(lines[8:15]), excerpt_line=9, excerpt_end_line=15, source_line_count=60
        )
    for index, (start, end) in enumerate([(1, 8), (16, 40), (41, 60)], 3):
        bundle["snippets"].append(
            dict(
                id=f"E{index}",
                role="expansion",
                path="LookupController.java",
                sha256="pinned",
                excerpt_line=start,
                excerpt_end_line=end,
                text="".join(lines[start - 1 : end]),
            )
        )
    return bundle, decision


def test_complete_expansion_enables_larger_java_file():
    bundle, decision = expanded_fixture()
    assert assess_evidence(bundle, decision)["passed"]


def test_expansion_gaps_conflicts_and_wrong_hash_fail():
    from traceproof.java_claims import complete_context

    for change in ["gap", "conflict", "hash", "count", "foreign"]:
        bundle, decision = expanded_fixture()
        if change == "gap":
            bundle["snippets"].pop()
        elif change == "conflict":
            conflicting = deepcopy(bundle["snippets"][0])
            conflicting["text"] = conflicting["text"].replace("GetMapping", "PutMapping")
            bundle["snippets"].append(conflicting)
        elif change == "hash":
            bundle["snippets"][-1]["sha256"] = "different"
        elif change == "count":
            bundle["snippets"][0]["source_line_count"] = 61
        else:
            bundle["snippets"][2]["text"] = bundle["snippets"][2]["text"].replace(
                "org.springframework.web.bind.annotation.RequestParam", "foreign.RequestParam"
            )
        assert not assess_evidence(bundle, decision)["passed"]
        if change != "foreign":
            assert complete_context(bundle, bundle["snippets"][0]) is None
