"""Source-anchored claim checks; passing is not a proof of exploitability or safety."""

import ast
import io
import textwrap
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GATE_VERSION = "1"
POLICIES = {
    "py/code-injection": {"class": "code_injection", "sinks": ["eval", "exec"]},
    "py/command-line-injection": {
        "class": "command_injection",
        "sinks": [
            "os.system",
            "os.popen",
            "subprocess.run",
            "subprocess.call",
            "subprocess.Popen",
            "subprocess.check_call",
            "subprocess.check_output",
        ],
    },
}


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    obligation: Literal["source", "sink", "flow", "guard", "counterevidence"]
    evidence_id: str = Field(min_length=1, max_length=20)
    line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=2000)
    assessment: Literal["present", "unknown"]
    explanation: str = Field(min_length=1, max_length=1000)


def requirements(rule_id):
    return {
        "gate_version": GATE_VERSION,
        "supported": rule_id in POLICIES,
        "policy": POLICIES.get(rule_id),
        "required": ["source", "sink", "flow", "guard"],
        "negative_requires": "present guard and quoted counterevidence",
        "scope": "quote, syntax and recorded flow consistency only; not runtime proof",
    }


def name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{name(node.value)}.{node.attr}"
    return "<dynamic>"


def anchors(window, claim, policy):
    """Recognize only a narrow syntax vocabulary, excluding comments/string literals."""
    text = textwrap.dedent(window)
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []
    result = []
    for node in ast.walk(tree):
        match = False
        if claim.obligation == "source":
            match = (
                isinstance(node, ast.Attribute)
                and name(node)
                in {
                    "request.args",
                    "request.form",
                    "request.data",
                    "request.json",
                    "request.GET",
                    "request.POST",
                }
            ) or (isinstance(node, ast.Call) and name(node.func) in {"input", "request.get_json"})
        elif claim.obligation == "sink" and isinstance(node, ast.Call):
            target = name(node.func)
            match = target in policy["sinks"]
            if target.startswith("subprocess."):
                match &= any(
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in node.keywords
                )
        elif claim.obligation in {"guard", "counterevidence"}:
            match = isinstance(node, (ast.If, ast.Assert, ast.Compare))
        if match:
            segment = ast.get_source_segment(text, node)
            if segment and segment in claim.quote:
                result.append((claim.line + node.lineno - 1, claim.line + node.end_lineno - 1))
    return result


def flow_nodes(bundle, snippet, ranges):
    return [
        node
        for node in bundle["snippets"]
        if node.get("flow_id") is not None
        and (
            snippet.get("flow_id") is None
            or (node["flow_id"] == snippet["flow_id"] and node["flow_step"] == snippet["flow_step"])
        )
        and node["path"] == snippet["path"]
        and node["sha256"] == snippet["sha256"]
        and any(start <= node["end_line"] and end >= node["line"] for start, end in ranges)
    ]


def assess_evidence(bundle, decision):
    report = {
        "gate_version": GATE_VERSION,
        "rule_id": bundle["rule_id"],
        "status": "insufficient_evidence",
        "passed": False,
        "checks": [],
        "missing": [],
        "unknowns": [],
        "reachability_proven": False,
        "scope": "quoted syntax and retained SARIF flow, not semantic entailment",
    }
    if decision.verdict == "abstain":
        return {**report, "status": "abstained"}
    if bundle["status"] != "ready":
        return {**report, "status": "incomplete_bundle"}
    policy = POLICIES.get(bundle["rule_id"])
    if policy is None:
        return {**report, "status": "unsupported_rule"}
    snippets = {item["id"]: item for item in bundle["snippets"]}
    satisfied, source_nodes, sink_nodes, flow_ids = set(), [], [], set()
    guard_present = False
    for claim in decision.claims:
        snippet = snippets.get(claim.evidence_id)
        reason = None
        located = []
        if snippet is None or claim.evidence_id not in decision.evidence_ids:
            reason = "unknown_or_uncited_evidence"
        elif (
            not claim.quote.strip()
            or not claim.explanation.strip()
            or not snippet["excerpt_line"]
            <= claim.line
            <= claim.end_line
            <= snippet["excerpt_end_line"]
            or claim.end_line - claim.line >= 40
        ):
            reason = "invalid_range_or_empty_claim"
        else:
            lines = io.StringIO(snippet["text"], newline="").readlines()
            window = "".join(
                lines[
                    claim.line - snippet["excerpt_line"] : claim.end_line
                    - snippet["excerpt_line"]
                    + 1
                ]
            )
            if claim.quote not in window:
                reason = "quote_mismatch"
            elif claim.assessment == "unknown":
                if claim.obligation == "guard":
                    satisfied.add("guard")
                    report["unknowns"].append("Guard effectiveness is unknown")
                else:
                    reason = "positive_evidence_required"
            elif claim.obligation == "flow":
                if (
                    snippet.get("flow_id") is None
                    or claim.line > snippet["end_line"]
                    or claim.end_line < snippet["line"]
                ):
                    reason = "not_a_recorded_flow_location"
                else:
                    flow_ids.add(snippet["flow_id"])
                    satisfied.add("flow")
            else:
                located = anchors(window, claim, policy)
                if not located:
                    reason = "supported_syntax_not_in_quote"
                else:
                    satisfied.add(claim.obligation)
                    if claim.obligation == "source":
                        source_nodes.extend(flow_nodes(bundle, snippet, located))
                    elif claim.obligation == "sink":
                        sink_nodes.extend(flow_nodes(bundle, snippet, located))
                    elif claim.obligation == "guard":
                        guard_present = True
        report["checks"].append(
            {
                "obligation": claim.obligation,
                "evidence_id": claim.evidence_id,
                "passed": reason is None,
                "reason": reason,
            }
        )
    linked = any(
        source["flow_id"] == sink["flow_id"]
        and source["flow_id"] in flow_ids
        and source["flow_step"] == 0
        and sink["flow_step"] == sink["flow_steps"] - 1
        for source in source_nodes
        for sink in sink_nodes
    )
    needed = {"source", "sink", "flow", "guard"}
    if decision.verdict == "likely_false_positive":
        needed.add("counterevidence")
        if not guard_present:
            report["missing"].append("present_guard")
    report["missing"].extend(sorted(needed - satisfied))
    if not linked:
        report["missing"].append("source_to_sink_recorded_flow")
    invalid = any(not check["passed"] for check in report["checks"])
    report["status"] = (
        "invalid_claims"
        if invalid
        else "insufficient_evidence"
        if report["missing"]
        else "supported_for_review"
    )
    report["passed"] = report["status"] == "supported_for_review"
    return report
