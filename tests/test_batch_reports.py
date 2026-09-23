import csv
import io
import json

import pytest
from conftest import row
from sqlalchemy import select
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from veriflow.batch_reports import import_reports, render_import_reports
from veriflow.cli import app
from veriflow.domain import TraceProofError
from veriflow.intake import submit
from veriflow.persistence import ImportItem, PublishedReport, Run, ScanAttempt
from veriflow.reports import publish_report


def test_exact_import_run_and_no_stale_fallback(store, scanned):
    repo, run, attempt, _ = scanned
    with store.transaction() as session:
        batch = session.scalar(select(ImportItem.import_id).where(ImportItem.run_id == run))
    assert import_reports(store, batch)["items"][0]["status"] == "report_not_published"
    report = publish_report(store, repo, run_id=run)
    result = import_reports(store, batch)
    item = result["items"][0]
    assert item["report_id"] == report["report_id"] and item["latest_attempt_id"] == attempt
    assert item["candidate_count"] == 1 and item["security_verdict"] == "not_adjudicated"
    output = CliRunner().invoke(app, ["--state-dir", str(store.root), "import-reports", batch])
    assert output.exit_code == 0 and json.loads(output.output) == result
    with store.transaction() as session:
        original = session.get(Run, run)
        session.add(
            Run(
                id="new-run",
                repo_id=repo,
                state=original.state,
                profile=original.profile,
                snapshot_id=original.snapshot_id,
                created_at="9999",
            )
        )
    assert import_reports(store, batch) == result
    with store.transaction() as session:
        session.add(
            ScanAttempt(id="new-failed", run_id=run, created_at="9999", report={"status": "failed"})
        )
    item = import_reports(store, batch)["items"][0]
    assert item["status"] == "report_not_published" and item["report_id"] is None
    assert item["analysis_status"] == "failed" and item["candidate_count"] is None
    failed = publish_report(store, repo, run_id=run)
    item = import_reports(store, batch)["items"][0]
    assert item["status"] == "published" and item["report_id"] == failed["report_id"]
    assert item["static_review_readiness"] != "ready_for_review"
    with store.transaction() as session:
        saved = session.get(PublishedReport, failed["report_id"])
        saved.content = {**saved.content, "candidate_count": 999}
    with pytest.raises(TraceProofError, match="integrity"):
        import_reports(store, batch)


def test_intake_gaps_pages_and_csv(store, archive, manifest):
    batch = submit(
        store,
        manifest([row(archive), row(archive, repo_id="bad", source_type="gcs")]),
        archive.parent,
        "inventory",
    )
    first = import_reports(store, batch, limit=1)
    assert first["counts"] == {"intake_not_ready": 1} and first["next_offset"] == 1
    last = import_reports(store, batch, offset=1, limit=1)
    assert last["items"][0]["intake_state"] == "rejected" and last["next_offset"] is None
    first["items"][0]["repo_id"] = " =formula"
    exported = list(csv.DictReader(io.StringIO(render_import_reports(first, "csv"))))
    assert exported[0]["repo_id"] == "' =formula" and exported[0]["candidate_count"] == ""
    empty = import_reports(store, batch, offset=100)
    assert empty["items"] == [] and len(render_import_reports(empty, "csv").splitlines()) == 1
    with pytest.raises(TraceProofError, match="Import not found"):
        import_reports(store, "missing")
    with pytest.raises(TraceProofError, match="pagination"):
        import_reports(store, batch, limit=0)
    with pytest.raises(TraceProofError, match="Format"):
        render_import_reports(first, "html")
