"""Read-only import report inventory scoped to the runs admitted in that import."""

import csv
import io
from collections import Counter

from sqlalchemy import func, select

from traceproof.domain import TraceProofError
from traceproof.history import validate_page
from traceproof.persistence import ImportBatch, ImportItem, PublishedReport, Run, ScanAttempt
from traceproof.reports import csv_cell, verified

FIELDS = (
    "import_id",
    "item_id",
    "row_number",
    "repo_id",
    "run_id",
    "intake_state",
    "status",
    "latest_attempt_id",
    "analysis_status",
    "report_id",
    "report_version",
    "static_review_readiness",
    "candidate_count",
    "security_verdict",
)


def import_reports(store, import_id, offset=0, limit=100):
    validate_page(offset, limit)
    with store.transaction() as session:
        if session.get(ImportBatch, import_id) is None:
            raise TraceProofError("Import not found")
        scope = ImportItem.import_id == import_id
        total = session.scalar(select(func.count()).select_from(ImportItem).where(scope))
        items = session.scalars(
            select(ImportItem)
            .where(scope)
            .order_by(ImportItem.row_number)
            .offset(offset)
            .limit(limit)
        ).all()
        rows = []
        for item in items:
            row = dict.fromkeys(FIELDS)
            row.update(
                import_id=import_id,
                item_id=item.id,
                row_number=item.row_number,
                run_id=item.run_id,
                intake_state=item.state,
                status="intake_not_ready",
            )
            run = session.get(Run, item.run_id) if item.run_id else None
            if run:
                row["repo_id"] = run.repo_id
            if run and item.state == "snapshotted":
                attempt = session.scalar(
                    select(ScanAttempt)
                    .where(ScanAttempt.run_id == run.id)
                    .order_by(ScanAttempt.created_at.desc(), ScanAttempt.id.desc())
                    .limit(1)
                )
                row.update(
                    status="not_analyzed" if attempt is None else "report_not_published",
                    latest_attempt_id=attempt.id if attempt else None,
                    analysis_status=attempt.report.get("status", "unknown") if attempt else None,
                )
                record = session.scalar(
                    select(PublishedReport)
                    .where(PublishedReport.run_id == run.id)
                    .order_by(PublishedReport.version.desc())
                    .limit(1)
                )
                if record:
                    report = verified(record)
                    if report["attempt_id"] == row["latest_attempt_id"]:
                        row.update(
                            status="published",
                            report_id=record.id,
                            report_version=record.version,
                            static_review_readiness=report.get("static_review_readiness", {}).get(
                                "state", "unknown"
                            ),
                            candidate_count=report.get("candidate_count"),
                            security_verdict=report.get("security_verdict", "not_adjudicated"),
                        )
            rows.append(row)
        return {
            "schema_version": "1",
            "import_id": import_id,
            "offset": offset,
            "limit": limit,
            "total_rows": total,
            "selected_rows": len(rows),
            "next_offset": offset + len(rows) if offset + len(rows) < total else None,
            "counts": dict(Counter(row["status"] for row in rows)),
            "items": rows,
            "scope": (
                "Latest published version only if it matches the admitted run's latest attempt; "
                "no fallback"
            ),
            "consistency": "One read transaction per page; later pages may observe new work",
        }


def render_import_reports(result, format="json"):
    if format == "json":
        return result
    if format != "csv":
        raise TraceProofError("Format must be json or csv")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: csv_cell(row[key]) for key in FIELDS} for row in result["items"])
    return output.getvalue()
