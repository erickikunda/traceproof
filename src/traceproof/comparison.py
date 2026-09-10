"""Compare immutable observations; absence never establishes remediation."""

import hashlib
from collections import defaultdict

from traceproof.bundles import canonical
from traceproof.domain import TraceProofError
from traceproof.reports import get_report, markdown_cell

COMPARISON_VERSION = "8"


def identity(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def reference(report, candidate):
    return {
        "occurrence_id": identity(
            [report["repo_id"], report["snapshot_id"], candidate["fingerprint"]]
        ),
        "fingerprint": candidate["fingerprint"],
        "rule_id": candidate["rule_id"],
        "path": candidate["path"],
        "line": candidate["line"],
        "latest_advisory": candidate["latest_advisory"],
        "latest_simulated": candidate.get("latest_simulated"),
        "adjudication": "unreviewed",
        "operator_review_state": candidate.get("operator_review_state", "not_reviewed"),
    }


def anchor(candidate):
    keys = ("tool_name", "tool_version", "rule_id", "path", "sha256", "line", "end_line")
    values = tuple(candidate.get(key) for key in keys)
    if any(value is None or value == "" or value == "unknown" for value in values):
        return None
    return values


def compatibility(before, after):
    gaps = []
    if before.get("language", "python") != after.get("language", "python"):
        gaps.append("language:different")
    if (before.get("language_scope") or {}).get("adapter_profile") != (
        after.get("language_scope") or {}
    ).get("adapter_profile"):
        gaps.append("extraction_profile:unknown_or_different")
    if ((before.get("language_scope") or {}).get("dependency_profile") or {}).get("id") != (
        (after.get("language_scope") or {}).get("dependency_profile") or {}
    ).get("id"):
        gaps.append("dependency_profile:unknown_or_different")
    if ((before.get("language_scope") or {}).get("java_dependency_profile") or {}).get("id") != (
        (after.get("language_scope") or {}).get("java_dependency_profile") or {}
    ).get("id"):
        gaps.append("java_dependency_profile:unknown_or_different")
    if (before.get("language_scope") or {}).get("network_isolation", "none") != (
        after.get("language_scope") or {}
    ).get("network_isolation", "none"):
        gaps.append("network_isolation:different")
    if (before.get("language_scope") or {}).get("evidence_gate") != (
        after.get("language_scope") or {}
    ).get("evidence_gate"):
        gaps.append("evidence_gate:unknown_or_different")
    for label, report in (("baseline", before), ("current", after)):
        if not report.get("snapshot_id"):
            gaps.append(f"{label}:snapshot_unknown")
        if report.get("analysis_status") != "completed" or not report.get("execution_complete"):
            gaps.append(f"{label}:analysis_incomplete")
        if report.get("candidate_count") is None:
            gaps.append(f"{label}:candidate_count_unknown")
        if report.get("static_review_readiness", {}).get("state") != "ready_for_review":
            gaps.append(f"{label}:static_review_readiness_unknown_or_incomplete")
    for key in ("profile", "query_sha256"):
        if not before.get(key) or not after.get(key) or before[key] != after[key]:
            gaps.append(f"{key}:unknown_or_different")
    inventories = [
        {(item.get("tool_name"), item.get("tool_version")) for item in report["candidates"]}
        for report in (before, after)
    ]
    if (
        not all(inventories)
        or inventories[0] != inventories[1]
        or any(
            value in (None, "", "unknown")
            for inventory in inventories
            for pair in inventory
            for value in pair
        )
    ):
        gaps.append("observed_tool_identity:unknown_or_different")
    if before["created_at"] > after["created_at"]:
        gaps.append("current_report_predates_baseline")
    return gaps


def compare_reports(store, repo_id, baseline_id, current_id):
    before = get_report(store, repo_id, baseline_id)
    after = get_report(store, repo_id, current_id)
    gaps = compatibility(before, after)
    left = {item["fingerprint"]: item for item in before["candidates"]}
    right = {item["fingerprint"]: item for item in after["candidates"]}
    rows = []

    def append(status, baseline, current, basis):
        rows.append(
            {
                "status": status,
                "basis": basis,
                "baseline": [reference(before, item) for item in baseline],
                "current": [reference(after, item) for item in current],
                "resolution_verified": False,
            }
        )

    # Exact snapshot-bound fingerprints identify the same stored observation, even when
    # analysis scope is incomplete. They say nothing about vulnerability truth.
    if before["snapshot_id"] and before["snapshot_id"] == after["snapshot_id"]:
        for fingerprint in sorted(left.keys() & right.keys()):
            append(
                "observed_in_both",
                [left.pop(fingerprint)],
                [right.pop(fingerprint)],
                "exact_snapshot_fingerprint",
            )
    if not gaps:
        groups = [defaultdict(list), defaultdict(list)]
        for group, candidates in zip(groups, (left, right), strict=True):
            for candidate in candidates.values():
                if key := anchor(candidate):
                    group[key].append(candidate)
        for key in sorted(groups[0].keys() & groups[1].keys()):
            old, new = groups[0][key], groups[1][key]
            if len(old) == len(new) == 1:
                append("possible_continuation", old, new, "same_unchanged_file_location")
            else:
                append("ambiguous", old, new, "multiple_candidates_at_same_source_anchor")
            for item in old:
                left.pop(item["fingerprint"])
            for item in new:
                right.pop(item["fingerprint"])
    for fingerprint in sorted(left):
        append("baseline_only", [left[fingerprint]], [], "not_observed_in_current_report")
    for fingerprint in sorted(right):
        append("current_only", [], [right[fingerprint]], "not_observed_in_baseline_report")
    counts = {
        status: sum(row["status"] == status for row in rows)
        for status in (
            "observed_in_both",
            "possible_continuation",
            "ambiguous",
            "baseline_only",
            "current_only",
        )
    }
    body = {
        "schema_version": "1",
        "comparison_version": COMPARISON_VERSION,
        "repo_id": repo_id,
        "baseline_report_id": baseline_id,
        "current_report_id": current_id,
        "baseline_snapshot_id": before["snapshot_id"],
        "current_snapshot_id": after["snapshot_id"],
        "scope": "candidate observations only",
        "scope_gaps": gaps,
        "anchor_matching_enabled": not gaps,
        "coverage_comparable": False,
        "baseline_analysis_status": before["analysis_status"],
        "current_analysis_status": after["analysis_status"],
        "baseline_candidate_count": before["candidate_count"],
        "current_candidate_count": after["candidate_count"],
        "baseline_rows_accounted": sum(len(row["baseline"]) for row in rows),
        "current_rows_accounted": sum(len(row["current"]) for row in rows),
        "group_counts": counts,
        "rows": rows,
        "limitations": [
            "Missing candidates are not verified fixes or proof of safety.",
            "Source-anchor matches are suggestions; findings are never merged.",
            "Line moves, renames and changed files are not automatically correlated.",
            "Entry-query hashes do not prove transitive query-pack equivalence.",
            "Coverage, resolution and vulnerability truth remain unverified.",
        ],
    }
    return {"comparison_id": identity(body), **body}


def render_comparison(report, format="json"):
    if format == "json":
        return canonical(report).decode()
    if format != "markdown":
        raise TraceProofError("Comparison format must be json or markdown")
    lines = [
        "# TraceProof report comparison",
        "",
        "**Observation changes only. No candidate is marked fixed or confirmed.**",
        "",
        f"Comparison: {report['comparison_id']}",
        "",
        f"Baseline report: {report['baseline_report_id']}",
        "",
        f"Current report: {report['current_report_id']}",
        "",
        "Scope gaps: " + markdown_cell(", ".join(report["scope_gaps"]) or "none in checked fields"),
        "",
        "| Status | Baseline observations | Current observations |",
        "| --- | --- | --- |",
    ]
    for row in report["rows"]:
        values = [row["status"]]
        for side in ("baseline", "current"):
            values.append(
                "; ".join(
                    f"{item['rule_id']} at {item['path']}:{item['line']} "
                    f"({item['latest_advisory']}, replay={item['latest_simulated']})"
                    f" operator review={item['operator_review_state']}"
                    for item in row[side]
                )
                or "none"
            )
        lines.append("| " + " | ".join(markdown_cell(value) for value in values) + " |")
    lines += ["", *["- " + item for item in report["limitations"]]]
    return "\n".join(lines) + "\n"
