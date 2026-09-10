"""Offline candidate-location scorecards; no scans or model calls."""

import csv
import hashlib
import io
from collections import Counter, defaultdict
from typing import Literal

from pydantic import Field, model_validator

from traceproof.benchmark import (
    BenchmarkLabels,
    BenchmarkManifest,
    StrictContract,
    read_contract,
    validate_pair,
)
from traceproof.bundles import canonical
from traceproof.domain import Digest, Identifier, TraceProofError
from traceproof.persistence import Snapshot
from traceproof.reports import csv_cell, get_report, markdown_cell

RULE_CWES = {"py/code-injection": {"CWE-94"}, "py/command-line-injection": {"CWE-78", "CWE-88"}}
MAX_CANDIDATES = 20000
MAX_PAIR_CHECKS = 1000000


class ReportSelection(StrictContract):
    repo_id: Identifier
    report_id: Digest


class EvaluationPlan(StrictContract):
    schema_version: Literal["1"]
    manifest_sha256: Digest
    query_sha256: Digest
    codeql_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", max_length=50)
    profile: Literal["standard"]
    rule_ids: list[Literal["py/code-injection", "py/command-line-injection"]] = Field(
        min_length=1, max_length=2
    )
    reports: list[ReportSelection] = Field(max_length=1000)

    @model_validator(mode="after")
    def unique(self):
        if len({item.repo_id for item in self.reports}) != len(self.reports) or len(
            set(self.rule_ids)
        ) != len(self.rule_ids):
            raise ValueError("Duplicate report repository or rule")
        return self


def scope_gaps(report, repository, plan):
    gaps = []
    for key, expected in (
        ("snapshot_id", repository.snapshot_id),
        ("profile", plan.profile),
        ("query_sha256", plan.query_sha256),
        ("analysis_codeql_version", plan.codeql_version),
    ):
        if report.get(key) != expected:
            gaps.append(f"{key}_mismatch_or_unknown")
    if report.get("static_review_readiness", {}).get("state") != "ready_for_review":
        gaps.append("static_review_incomplete")
    if report.get("analysis_status") != "completed" or report.get("execution_complete") is not True:
        gaps.append("analysis_incomplete")
    if report.get("candidate_count") is None:
        gaps.append("candidate_count_unknown")
    if repository.languages != ["python"]:
        gaps.append("language_scope_unsupported")
    return gaps


def evaluate_benchmark(store, manifest_path, labels_path, plan_path):
    manifest = read_contract(manifest_path, BenchmarkManifest)
    labels = read_contract(labels_path, BenchmarkLabels)
    manifest_digest = validate_pair(manifest, labels)
    plan = read_contract(plan_path, EvaluationPlan)
    if plan.manifest_sha256 != manifest_digest:
        raise TraceProofError("Evaluation plan does not match benchmark manifest")
    selections = {item.repo_id: item.report_id for item in plan.reports}
    if selections.keys() - {item.repo_id for item in manifest.repositories}:
        raise TraceProofError("Evaluation selection contains a repository outside the manifest")
    by_repo = defaultdict(list)
    for label in labels.labels:
        by_repo[label.repo_id].append(label)
    scope_cwes = set().union(*(RULE_CWES[rule] for rule in plan.rule_ids))
    repository_rows, label_rows, candidate_rows = [], [], []
    candidates_seen = pair_checks = 0
    for repository in manifest.repositories:
        selected = selections.get(repository.repo_id)
        # Invalid ownership/IDs/integrity are request errors, not fabricated missing results.
        report = get_report(store, repository.repo_id, selected) if selected else None
        gaps = scope_gaps(report, repository, plan) if report else ["report_not_selected"]
        candidates = report["candidates"] if report else []
        candidates_seen += len(candidates)
        if candidates_seen > MAX_CANDIDATES:
            raise TraceProofError("Evaluation exceeds 20,000 candidate rows")
        with store.transaction() as session:
            snapshot = session.get(Snapshot, repository.snapshot_id)
            files = (
                {item["path"]: item["sha256"] for item in snapshot.manifest["files"]}
                if snapshot and snapshot.repo_id == repository.repo_id
                else {}
            )
        if not files:
            gaps.append("snapshot_metadata_missing")
        buckets = defaultdict(list)
        for candidate in candidates:
            if candidate["rule_id"] in plan.rule_ids:
                for cwe in RULE_CWES[candidate["rule_id"]]:
                    buckets[(candidate.get("path"), candidate.get("sha256"), cwe)].append(candidate)
        edges, reverse = {}, defaultdict(list)
        local_rows = []
        for label in by_repo[repository.repo_id]:
            reasons = list(gaps)
            if label.cwe not in scope_cwes:
                reasons.append("weakness_not_evaluated_by_selected_rules")
            if files.get(label.path) != label.file_sha256:
                reasons.append("label_file_digest_mismatch_or_missing")
            row = {
                "repo_id": repository.repo_id,
                "label_id": label.label_id,
                "cwe": label.cwe,
                "status": "not_evaluable" if reasons else "not_observed",
                "reasons": reasons,
                "candidate_fingerprints": [],
            }
            local_rows.append(row)
            if reasons:
                continue
            eligible = buckets[(label.path, label.file_sha256, label.cwe)]
            pair_checks += len(eligible)
            if pair_checks > MAX_PAIR_CHECKS:
                raise TraceProofError("Evaluation exceeds bounded location comparisons")
            matches = [
                candidate["fingerprint"]
                for candidate in eligible
                if type(candidate.get("line")) is int
                and type(candidate.get("end_line")) is int
                and candidate["line"] <= label.end_line
                and candidate["end_line"] >= label.line
            ]
            edges[label.label_id] = matches
            for fingerprint in matches:
                reverse[fingerprint].append(label.label_id)
        matched = set()
        for row in local_rows:
            matches = edges.get(row["label_id"], [])
            row["candidate_fingerprints"] = sorted(matches)
            if matches:
                if len(matches) == 1 and len(reverse[matches[0]]) == 1:
                    row["status"] = "matched_location"
                    matched.add(matches[0])
                else:
                    row["status"] = "ambiguous"
        for candidate in candidates:
            fingerprint = candidate["fingerprint"]
            candidate_rows.append(
                {
                    "repo_id": repository.repo_id,
                    "fingerprint": fingerprint,
                    "status": "matched_location"
                    if fingerprint in matched
                    else "ambiguous"
                    if fingerprint in reverse
                    else "unjudged",
                    "adjudication": "unreviewed",
                }
            )
        label_rows.extend(local_rows)
        repository_rows.append(
            {
                "repo_id": repository.repo_id,
                "report_id": selected,
                "status": "not_evaluable"
                if gaps
                else "partial"
                if any(row["status"] == "not_evaluable" for row in local_rows)
                else "evaluated",
                "scope_gaps": gaps,
                "candidate_count": report.get("candidate_count") if report else None,
                "label_counts": dict(Counter(row["status"] for row in local_rows)),
            }
        )
    counts = Counter(row["status"] for row in label_rows)
    total = len(label_rows)
    body = {
        "schema_version": "1",
        "evaluator_version": "1",
        "report_kind": "candidate_location_scorecard",
        "manifest_sha256": manifest_digest,
        "labels_sha256": hashlib.sha256(canonical(labels.model_dump())).hexdigest(),
        "plan_sha256": hashlib.sha256(canonical(plan.model_dump())).hexdigest(),
        "dataset_id": manifest.dataset_id,
        "dataset_version": manifest.dataset_version,
        "label_set_version": labels.label_set_version,
        "evaluation_scope": {
            key: plan.model_dump()[key]
            for key in ("query_sha256", "codeql_version", "profile", "rule_ids")
        },
        "repository_count": len(repository_rows),
        "label_count": total,
        "label_counts": {
            key: counts[key]
            for key in ("matched_location", "not_observed", "ambiguous", "not_evaluable")
        },
        "candidate_counts": dict(Counter(row["status"] for row in candidate_rows)),
        "candidate_recall_proxy": {
            "numerator": counts["matched_location"],
            "denominator": total,
            "value": counts["matched_location"] / total if total else None,
        },
        "complete": all(row["status"] == "evaluated" for row in repository_rows)
        and not counts["ambiguous"]
        and not counts["not_evaluable"],
        "precision": None,
        "confirmed_recall": None,
        "repositories": repository_rows,
        "labels": label_rows,
        "candidates": candidate_rows,
        "limitations": [
            "Location matches are provisional; root-cause and symbol equivalence are not proven.",
            "Recall proxy includes all declared labels, including failed or missing scans.",
            "Additional predictions are unjudged, never automatic false positives.",
            "Entry-query pins do not cover transitive query-pack dependencies.",
            "No benchmark scans or model calls are dispatched by this evaluator.",
        ],
    }
    encoded = canonical(body)
    if len(encoded) > 8 * 1024 * 1024:
        raise TraceProofError("Evaluation scorecard exceeds 8 MiB")
    return {"scorecard_id": hashlib.sha256(encoded).hexdigest(), **body}


def render_scorecard(report, format="json"):
    if format == "json":
        return canonical(report).decode()
    if format in {"summary-csv", "repositories-csv", "labels-csv", "candidates-csv"}:
        return scorecard_csv(report, format)
    if format != "markdown":
        raise TraceProofError(
            "Scorecard format must be json, markdown, summary-csv, repositories-csv, "
            "labels-csv or candidates-csv"
        )
    metric = report["candidate_recall_proxy"]
    lines = [
        "# TraceProof candidate-location scorecard",
        "",
        "**Provisional location matches; precision and confirmed recall are unknown.**",
        "",
        f"Scorecard: {report['scorecard_id']}",
        "",
        f"Candidate recall proxy: {metric['numerator']} / {metric['denominator']}",
        "",
        f"Evaluation complete: {report['complete']}",
        "",
        "| Repository | Status | Labels |",
        "| --- | --- | --- |",
    ]
    for row in report["repositories"]:
        lines.append(
            "| "
            + " | ".join(
                markdown_cell(value)
                for value in (row["repo_id"], row["status"], str(row["label_counts"]))
            )
            + " |"
        )
    lines.extend(["", *["- " + item for item in report["limitations"]]])
    return "\n".join(lines) + "\n"


def scorecard_csv(report, format):
    """Separate data grains with stable provenance; blank cells preserve unknown values."""
    common = {
        "export_schema_version": "1",
        "grain": format.removesuffix("-csv"),
        **{
            key: report[key]
            for key in (
                "scorecard_id",
                "evaluator_version",
                "dataset_id",
                "dataset_version",
                "label_set_version",
                "manifest_sha256",
                "labels_sha256",
                "plan_sha256",
            )
        },
    }
    if format == "summary-csv":
        metric = report["candidate_recall_proxy"]
        rows = [
            {
                "repository_count": report["repository_count"],
                "label_count": report["label_count"],
                "complete": report["complete"],
                "candidate_recall_proxy_numerator": metric["numerator"],
                "candidate_recall_proxy_denominator": metric["denominator"],
                "candidate_recall_proxy_value": metric["value"],
                "precision": report["precision"],
                "confirmed_recall": report["confirmed_recall"],
                "label_counts": report["label_counts"],
                "candidate_counts": report["candidate_counts"],
                "evaluation_scope": report["evaluation_scope"],
            }
        ]
        fields = list(rows[0])
    else:
        grain = format.removesuffix("-csv")
        fields = {
            "repositories": [
                "repo_id",
                "report_id",
                "status",
                "scope_gaps",
                "candidate_count",
                "label_counts",
            ],
            "labels": ["repo_id", "label_id", "cwe", "status", "reasons", "candidate_fingerprints"],
            "candidates": ["repo_id", "fingerprint", "status", "adjudication"],
        }[grain]
        rows = report[grain]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=[*common, *fields], lineterminator="\n")
    writer.writeheader()
    for row in rows:
        values = {**common, **{key: row[key] for key in fields}}
        writer.writerow(
            {
                key: csv_cell(
                    canonical(value).decode() if isinstance(value, (dict, list)) else value
                )
                for key, value in values.items()
            }
        )
    return output.getvalue()
