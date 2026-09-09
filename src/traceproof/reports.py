"""Immutable summary reports. No source reads, analysis or model calls during publication."""

import csv
import hashlib
import html
import io
import json
from collections import Counter

from sqlalchemy import func, select

from traceproof.bundles import canonical
from traceproof.domain import TraceProofError
from traceproof.intake import now
from traceproof.persistence import (
    Candidate,
    EvidenceBundle,
    ImportItem,
    OperatorReview,
    PublishedReport,
    Run,
    ScanAttempt,
    Snapshot,
    TriageCall,
    exclusive_worker,
)
from traceproof.readiness import static_readiness
from traceproof.reviews import verified_review

MAX_ROWS = 10000
MAX_REPORT_BYTES = 8 * 1024 * 1024


def selected_run(session, repo_id, run_id=None):
    query = select(Run).where(Run.repo_id == repo_id)
    if run_id:
        query = query.where(Run.id == run_id)
    run = session.scalar(query.order_by(Run.created_at.desc(), Run.id.desc()).limit(1))
    if run is None:
        raise TraceProofError("Repository/run not found")
    return run


def bounded(session, query):
    rows = list(session.scalars(query.limit(MAX_ROWS + 1)))
    if len(rows) > MAX_ROWS:
        raise TraceProofError("Report exceeds 10,000 rows; no partial report was published")
    return rows


def projection(session, repo_id, run_id, attempt_id):
    run = selected_run(session, repo_id, run_id)
    latest = selected_run(session, repo_id)
    attempts = select(ScanAttempt).where(ScanAttempt.run_id == run.id)
    latest_attempt = session.scalar(
        attempts.order_by(ScanAttempt.created_at.desc(), ScanAttempt.id.desc()).limit(1)
    )
    attempt = (
        latest_attempt
        if attempt_id is None
        else session.scalar(attempts.where(ScanAttempt.id == attempt_id))
    )
    if attempt_id is not None and attempt is None:
        raise TraceProofError("Attempt does not belong to selected run")
    scan = attempt.report if attempt else {}
    candidates = (
        bounded(
            session,
            select(Candidate)
            .where(Candidate.attempt_id == attempt.id)
            .order_by(Candidate.fingerprint),
        )
        if attempt
        else []
    )
    calls = (
        bounded(
            session,
            select(TriageCall)
            .join(EvidenceBundle, TriageCall.bundle_id == EvidenceBundle.id)
            .join(Candidate, EvidenceBundle.candidate_id == Candidate.id)
            .where(Candidate.attempt_id == attempt.id, TriageCall.run_id == run.id)
            .order_by(TriageCall.created_at, TriageCall.id),
        )
        if attempt
        else []
    )
    bundle_candidates = (
        dict(
            session.execute(
                select(EvidenceBundle.id, EvidenceBundle.candidate_id)
                .join(Candidate, EvidenceBundle.candidate_id == Candidate.id)
                .join(TriageCall, TriageCall.bundle_id == EvidenceBundle.id)
                .where(Candidate.attempt_id == attempt.id, TriageCall.run_id == run.id)
            ).all()
        )
        if attempt
        else {}
    )
    history = {}
    for call in calls:
        result = call.result
        gate = result.get("evidence_gate") or {}
        # Deliberately omit model prose, source quotes, endpoint config and local paths.
        entry = {
            "call_id": call.id,
            "bundle_id": call.bundle_id,
            "created_at": call.created_at,
            "state": call.state,
            "disposition": result.get("disposition", "abstain"),
            "simulated": result.get("simulated"),
            "gate_version": result.get("gate_version"),
            "gate_status": gate.get("status"),
            "gate_passed": gate.get("passed"),
            "prompt_version": result.get("prompt_version"),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "config_sha256": result.get("config_sha256"),
            "request_sha256": call.request_sha256,
            "usage": result.get("usage"),
            "accounted_micro_usd": call.charged_micro_usd,
        }
        history.setdefault(bundle_candidates[call.bundle_id], []).append(entry)
    review_records = (
        bounded(
            session,
            select(OperatorReview)
            .join(Candidate)
            .where(Candidate.attempt_id == attempt.id)
            .order_by(OperatorReview.revision),
        )
        if attempt
        else []
    )
    operator_history = {}
    for record in review_records:
        review = verified_review(record)
        operator_history.setdefault(record.candidate_id, []).append(
            {
                key: review[key]
                for key in (
                    "review_id",
                    "revision",
                    "state",
                    "created_at",
                    "bundle_id",
                    "evidence_ids",
                    "reviewer_authenticated",
                    "independently_verified",
                )
            }
        )
    rows = []
    for candidate in candidates:
        evidence = candidate.evidence
        location = evidence.get("evidence") or {}
        decisions = history.get(candidate.id, [])
        reviews = operator_history.get(candidate.id, [])
        rows.append(
            {
                "fingerprint": candidate.fingerprint,
                "rule_id": evidence["rule_id"],
                "tool_name": evidence.get("tool_name"),
                "tool_version": evidence.get("tool_version"),
                "path": location.get("path"),
                "line": location.get("line"),
                "end_line": location.get("end_line"),
                "sha256": location.get("sha256"),
                "location_status": evidence.get("location_status"),
                "suppressed_by_tool": evidence.get("suppressed", False),
                "adjudication": "unreviewed",
                "operator_review_state": reviews[-1]["state"] if reviews else "not_reviewed",
                "operator_review_history": reviews,
                "triage_history": decisions,
                "latest_advisory": decisions[-1]["disposition"] if decisions else "not_triaged",
                "latest_simulated": decisions[-1]["simulated"] if decisions else None,
            }
        )
    snapshot = session.get(Snapshot, run.snapshot_id) if run.snapshot_id else None
    admitted = session.scalar(
        select(ImportItem).where(ImportItem.run_id == run.id).order_by(ImportItem.id).limit(1)
    )
    candidate_count = scan.get("candidate_count")
    if candidate_count is not None and candidate_count != len(rows):
        raise TraceProofError("Stored candidate count does not reconcile; report not published")
    return {
        "schema_version": "1",
        "projection_version": "4",
        "report_kind": "repository_summary",
        "repo_id": repo_id,
        "run_id": run.id,
        "snapshot_id": run.snapshot_id,
        "profile": run.profile,
        "owner": (admitted.spec or {}).get("owner") if admitted else None,
        "classification": snapshot.manifest.get("classification") if snapshot else None,
        "run_state": run.state,
        "attempt_id": attempt.id if attempt else None,
        "latest_run_id_at_publication": latest.id,
        "latest_attempt_id_at_publication": latest_attempt.id if latest_attempt else None,
        "analysis_status": scan.get("status", "not_started"),
        "execution_complete": scan.get("execution_complete", False),
        "candidate_count": candidate_count,
        "candidate_rows": len(rows),
        "operator_review_counts": dict(Counter(row["operator_review_state"] for row in rows)),
        "verified_finding_count": None,
        "security_verdict": "not_adjudicated",
        "coverage_verified": False,
        "static_review_readiness": static_readiness(session, run.snapshot_id, scan),
        "diagnostic_errors": scan.get("diagnostic_errors"),
        "diagnostic_warnings": scan.get("diagnostic_warnings"),
        "unmapped_candidates": scan.get("unmapped_candidates"),
        "query_sha256": scan.get("query_sha256"),
        "analysis_codeql_version": scan.get("analysis_codeql_version"),
        "sarif_sha256": scan.get("sarif_sha256"),
        "triage_call_count": len(calls),
        "simulated_micro_usd": sum(
            c.charged_micro_usd for c in calls if c.result.get("simulated") is True
        ),
        "live_accounted_micro_usd": sum(
            c.charged_micro_usd for c in calls if c.result.get("simulated") is False
        ),
        "unknown_mode_micro_usd": sum(
            c.charged_micro_usd for c in calls if c.result.get("simulated") is None
        ),
        "cost_scope": "selected attempt only; accounted amounts are not provider invoices",
        "candidates": rows,
        "limitations": [
            "Raw candidates stay unreviewed; operator reviews are separate assertions.",
            "Zero candidates is not a clean security verdict; coverage is not proven.",
            "Source excerpts, model prose and raw diagnostics are excluded from this summary.",
            "Freshness describes publication time; exact report retrieval is immutable.",
        ],
    }


def publish_report(store, repo_id, run_id=None, attempt_id=None):
    store.require_initialized()
    with exclusive_worker(store.root), store.transaction() as session:
        body = projection(session, repo_id, run_id, attempt_id)
        digest = hashlib.sha256(canonical(body)).hexdigest()
        existing = session.scalar(
            select(PublishedReport).where(
                PublishedReport.run_id == body["run_id"], PublishedReport.input_digest == digest
            )
        )
        if existing:
            return verified(existing)
        version = 1 + (
            session.scalar(
                select(func.max(PublishedReport.version)).where(
                    PublishedReport.run_id == body["run_id"]
                )
            )
            or 0
        )
        content = {**body, "report_version": version, "created_at": now()}
        encoded = canonical(content)
        if len(encoded) > MAX_REPORT_BYTES:
            raise TraceProofError("Report exceeds 8 MiB; no partial report was published")
        identity = hashlib.sha256(encoded).hexdigest()
        record = PublishedReport(
            id=identity,
            run_id=body["run_id"],
            version=version,
            input_digest=digest,
            created_at=content["created_at"],
            content=content,
        )
        session.add(record)
        return verified(record)


def verified(record):
    if hashlib.sha256(canonical(record.content)).hexdigest() != record.id:
        raise TraceProofError("Report integrity check failed")
    return {"report_id": record.id, **record.content}


def get_report(store, repo_id, report_id=None, run_id=None):
    with store.transaction() as session:
        if report_id:
            record = session.scalar(
                select(PublishedReport)
                .join(Run)
                .where(PublishedReport.id == report_id, Run.repo_id == repo_id)
            )
            if record is None or (run_id and record.run_id != run_id):
                raise TraceProofError("Report does not belong to repository/run")
        else:
            run = selected_run(session, repo_id, run_id)
            record = session.scalar(
                select(PublishedReport)
                .where(PublishedReport.run_id == run.id)
                .order_by(PublishedReport.version.desc())
                .limit(1)
            )
            if record is None:
                raise TraceProofError("No published report for selected run; no fallback was used")
            verified(record)
            latest_attempt = session.scalar(
                select(ScanAttempt.id)
                .where(ScanAttempt.run_id == run.id)
                .order_by(ScanAttempt.created_at.desc(), ScanAttempt.id.desc())
                .limit(1)
            )
            if record.content["attempt_id"] != latest_attempt:
                raise TraceProofError(
                    "Latest attempt has no current report; publish it or select an exact report ID"
                )
        return verified(record)


def report_history(store, repo_id, offset=0, limit=100):
    if offset < 0 or not 1 <= limit <= 1000:
        raise TraceProofError("Invalid report pagination")
    with store.transaction() as session:
        selected_run(session, repo_id)
        query = select(PublishedReport).join(Run).where(Run.repo_id == repo_id)
        rows = session.scalars(
            query.order_by(PublishedReport.created_at.desc(), PublishedReport.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return {
            "repo_id": repo_id,
            "offset": offset,
            "limit": limit,
            "reports": [
                {
                    "report_id": row.id,
                    "run_id": row.run_id,
                    "report_version": row.version,
                    "created_at": row.created_at,
                }
                for row in rows
            ],
        }


def csv_cell(value):
    text = "" if value is None else str(value)
    # Quoting alone does not neutralize spreadsheet formulas, including whitespace prefixes.
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n"))
        else text
    )


def markdown_cell(value):
    text = html.escape("unknown" if value is None else str(value))
    for character in "\\`*_{}[]()#+-.!|":
        text = text.replace(character, f"&#{ord(character)};")
    return text.replace("\n", " ").replace("\r", " ")


def render_report(report, format="json"):
    if format == "json":
        return canonical(report).decode()
    if format in {"scan-csv", "candidates-csv"}:
        common = {
            key: report[key]
            for key in (
                "report_id",
                "report_version",
                "schema_version",
                "repo_id",
                "run_id",
                "snapshot_id",
                "analysis_status",
                "candidate_count",
                "verified_finding_count",
                "coverage_verified",
            )
        }
        common["static_review_readiness"] = report.get("static_review_readiness", {}).get(
            "state", "unknown"
        )
        fields = list(common)
        if format == "candidates-csv":
            fields += [
                "fingerprint",
                "rule_id",
                "path",
                "line",
                "adjudication",
                "latest_advisory",
                "latest_simulated",
                "operator_review_state",
            ]
            rows = [
                {**common, **{key: item.get(key) for key in fields if key not in common}}
                for item in report["candidates"]
            ]
        else:
            rows = [common]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: csv_cell(value) for key, value in row.items()} for row in rows)
        return output.getvalue()
    # Render every summary field, including history, without treating untrusted text as markup.
    pretty = json.dumps(report, indent=2, ensure_ascii=False)
    notice = "NOT INDEPENDENTLY VERIFIED — operator reviews are separate assertions."
    readiness = report.get("static_review_readiness", {}).get("state", "unknown")
    summary = (
        f"Repository: {report['repo_id']} | Analysis: {report['analysis_status']} | "
        f"Candidates: {report['candidate_count']} | Coverage verified: false | "
        f"Static review readiness: {readiness}"
    )
    headings = [
        "Rule",
        "Location",
        "Static status",
        "Operator review",
        "Latest advisory",
        "Mode",
        "Triage calls",
    ]
    rows = [
        [
            item["rule_id"],
            f"{item['path'] or 'unmapped'}:{item['line'] or '?'}",
            item["adjudication"],
            item.get("operator_review_state", "not_reviewed"),
            item["latest_advisory"],
            "replay"
            if item.get("latest_simulated") is True
            else "live"
            if item.get("latest_simulated") is False
            else "unknown / not triaged",
            len(item["triage_history"]),
        ]
        for item in report["candidates"]
    ]
    metadata = (
        f"Owner: {report['owner']} | Classification: {report['classification']} | "
        f"Version: {report['report_version']}"
    )
    if format == "markdown":
        safe = html.escape(pretty).replace("`", "&#96;")
        table = (
            "| " + " | ".join(headings) + " |\n| " + " | ".join(["---"] * len(headings)) + " |\n"
        )
        table += "\n".join(
            "| " + " | ".join(markdown_cell(cell) for cell in row) + " |" for row in rows
        )
        return (
            f"# TraceProof repository report\n\n**{notice}**\n\n"
            + markdown_cell(summary)
            + "\n\n"
            + markdown_cell(metadata)
            + "\n\n"
            + table
            + "\n\nDetails and advisory history:\n\n"
            + f"```text\n{safe}\n```\n"
        )
    if format == "html":
        table = (
            "<table><thead><tr>"
            + "".join(f"<th>{heading}</th>" for heading in headings)
            + "</tr></thead><tbody>"
        )
        table += "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        table += "</tbody></table>"
        return (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
            'style-src &#39;unsafe-inline&#39;">'
            "<title>TraceProof repository report</title><style>body{font:16px system-ui;"
            "max-width:1100px;margin:2rem auto;padding:1rem}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f4f6;padding:1rem}"
            "table{border-collapse:collapse;width:100%}th,td{text-align:left;"
            "border-bottom:1px solid #ddd;padding:.6rem;overflow-wrap:anywhere}</style>"
            f"<h1>TraceProof repository report</h1><p><strong>{notice}</strong></p>"
            f"<p>{html.escape(summary)}</p><p>{html.escape(metadata)}</p>{table}"
            "<details><summary>Report details and advisory history</summary>"
            f"<pre>{html.escape(pretty)}</pre></details></html>"
        )
    raise TraceProofError("Format must be json, markdown, html, scan-csv or candidates-csv")
