import json

import pytest
from conftest import row
from test_intake import run_worker
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from traceproof import batch_scan, pipeline
from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.intake import submit


def test_mixed_rows_pagination_and_explicit_rescan(store, archive, manifest, tmp_path, monkeypatch):
    batch = submit(
        store,
        manifest(
            [
                row(archive),
                row(archive, repo_id="second"),
                row(archive, repo_id="bad", source_type="gcs"),
            ]
        ),
        archive.parent,
        "batch",
    )
    run_worker(store, batch)
    query = tmp_path / "query.ql"
    query.write_text("// synthetic")
    calls = []

    def scan(*args, **kwargs):
        calls.append(kwargs["skip_existing"])
        if len(calls) == 1:
            raise TraceProofError("Synthetic row failure")
        return {"status": "ready_for_review", "report_id": "report"}

    monkeypatch.setattr(batch_scan, "scan_run", scan)
    result = batch_scan.scan_import(store, batch, query, limit=3)
    assert [item["status"] for item in result["items"]] == [
        "row_error",
        "ready_for_review",
        "skipped_intake_not_ready",
    ]
    assert calls == [True, True] and result["next_offset"] is None
    page = batch_scan.scan_import(store, batch, query, limit=1, rescan=True)
    assert page["next_offset"] == 1 and calls[-1] is False
    assert batch_scan.scan_import(store, batch, query, offset=100)["items"] == []
    output = CliRunner().invoke(
        app, ["--state-dir", str(store.root), "scan-import", batch, str(query), "--offset", "2"]
    )
    assert output.exit_code == 0 and json.loads(output.output)["selected_rows"] == 1


def test_existing_attempt_skipped_before_index_or_tools(store, scanned, tmp_path, monkeypatch):
    query = tmp_path / "query.ql"
    query.write_text("// synthetic")

    def forbidden(*args, **kwargs):
        pytest.fail("Existing attempt should skip work")

    monkeypatch.setattr(pipeline, "build_index", forbidden)
    result = pipeline.scan_run(store, scanned[1], query, skip_existing=True)
    assert result["status"] == "skipped_existing_attempt"
    assert result["attempt_id"] == scanned[2] and result["report_id"] is None


def test_uncaptured_rows_and_invalid_pages(store, archive, manifest, tmp_path, monkeypatch):
    batch = submit(store, manifest([row(archive)]), archive.parent, "not-captured")
    query = tmp_path / "query.ql"
    query.write_text("// synthetic")
    monkeypatch.setattr(batch_scan, "scan_run", lambda *a, **kw: pytest.fail("Uncaptured input"))
    assert batch_scan.scan_import(store, batch, query)["counts"] == {"skipped_intake_not_ready": 1}
    with pytest.raises(TraceProofError, match="pagination"):
        batch_scan.scan_import(store, batch, query, limit=0)
