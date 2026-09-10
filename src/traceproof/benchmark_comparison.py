"""Compare exact evaluator publications without rerunning evaluation or scanning."""

from collections import Counter

from traceproof.bundles import canonical
from traceproof.domain import TraceProofError
from traceproof.reports import markdown_cell
from traceproof.scorecards import get_scorecard


def compare_scorecards(store, dataset_id, baseline_id, current_id):
    baseline = get_scorecard(store, dataset_id, baseline_id)
    current = get_scorecard(store, dataset_id, current_id)
    reasons = []
    for key in ("schema_version", "evaluator_version", "manifest_sha256", "labels_sha256"):
        if baseline.get(key) != current.get(key):
            reasons.append(f"{key}_changed")
    for side, report in (("baseline", baseline), ("current", current)):
        if report.get("complete") is not True:
            reasons.append(f"{side}_incomplete")
        if not report["candidate_recall_proxy"]["denominator"]:
            reasons.append(f"{side}_has_no_labels")
    if baseline["evaluation_scope"]["profile"] != current["evaluation_scope"]["profile"]:
        reasons.append("profile_changed")
    if set(baseline["evaluation_scope"]["rule_ids"]) != set(
        current["evaluation_scope"]["rule_ids"]
    ):
        reasons.append("selected_rules_changed")
    old = {(row["repo_id"], row["label_id"]): row for row in baseline["labels"]}
    new = {(row["repo_id"], row["label_id"]): row for row in current["labels"]}
    if old.keys() != new.keys():
        reasons.append("label_population_changed")
    changes = {
        key: {
            "baseline": baseline["evaluation_scope"].get(key),
            "current": current["evaluation_scope"].get(key),
        }
        for key in sorted(set(baseline["evaluation_scope"]) | set(current["evaluation_scope"]))
        if baseline["evaluation_scope"].get(key) != current["evaluation_scope"].get(key)
    }
    rows = []
    if not reasons:
        for key in sorted(old):
            before, after = old[key]["status"], new[key]["status"]
            rows.append(
                {
                    "repo_id": key[0],
                    "label_id": key[1],
                    "cwe": new[key]["cwe"],
                    "baseline_status": before,
                    "current_status": after,
                    "transition": "unchanged"
                    if before == after
                    else "location_match_gained"
                    if after == "matched_location"
                    else "location_match_lost"
                    if before == "matched_location"
                    else "status_changed",
                }
            )
    old_metric, new_metric = baseline["candidate_recall_proxy"], current["candidate_recall_proxy"]
    result = {
        "schema_version": "1",
        "comparison_kind": "benchmark_location_proxy",
        "dataset_id": dataset_id,
        "baseline_scorecard_id": baseline_id,
        "current_scorecard_id": current_id,
        "status": "not_comparable" if reasons else "comparable",
        "reasons": reasons,
        "analysis_configuration_changes": changes,
        "baseline_metric": old_metric,
        "current_metric": new_metric,
        "matched_label_delta": None
        if reasons
        else new_metric["numerator"] - old_metric["numerator"],
        "recall_proxy_delta": None if reasons else new_metric["value"] - old_metric["value"],
        "transition_counts": dict(Counter(row["transition"] for row in rows)),
        "labels": rows,
        "precision_delta": None,
        "confirmed_recall_delta": None,
        "limitations": [
            "Location-match changes are provisional, not confirmed discoveries or fixes.",
            "Query and CodeQL version changes are disclosed; causation is not established.",
            "Cost and latency comparison are not supported by these scorecards.",
        ],
    }
    if len(canonical(result)) > 8 * 1024 * 1024:
        raise TraceProofError("Benchmark comparison exceeds 8 MiB")
    return result


def render_comparison(report, format="json"):
    if format == "json":
        return canonical(report).decode()
    if format != "markdown":
        raise TraceProofError("Benchmark comparison format must be json or markdown")
    lines = [
        "# TraceProof benchmark comparison",
        "",
        "Provisional location matches; precision and confirmed recall remain unknown.",
        "",
    ]
    for key in (
        "baseline_scorecard_id",
        "current_scorecard_id",
        "status",
        "reasons",
        "analysis_configuration_changes",
        "matched_label_delta",
        "recall_proxy_delta",
    ):
        lines.append(f"- {key}: {markdown_cell(report[key])}")
    lines.extend(
        [
            "",
            "| Repository | Label | Baseline | Current | Transition |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["labels"]:
        lines.append(
            "| "
            + " | ".join(
                markdown_cell(
                    row[key].replace("_", " ")
                    if key.endswith("status") or key == "transition"
                    else row[key]
                )
                for key in (
                    "repo_id",
                    "label_id",
                    "baseline_status",
                    "current_status",
                    "transition",
                )
            )
            + " |"
        )
    lines.extend(["", *["- " + item for item in report["limitations"]]])
    return "\n".join(lines) + "\n"
