from types import SimpleNamespace

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from traceproof import pipeline
from traceproof.domain import TraceProofError
from traceproof.languages import adapter_for, language_scope, validate_extraction_scope
from traceproof.persistence import ScanAttempt
from traceproof.reports import get_report, publish_report, render_report


def manifest(*paths):
    return SimpleNamespace(snapshot_id="pinned", files=[SimpleNamespace(path=p) for p in paths])


def test_inventory_and_explicit_capabilities():
    scope = language_scope(manifest("A.java", "app.py", "web.ts", "main.go", "README.md"), "java")
    assert scope["selected_file_count"] == 1
    assert scope["unselected_languages"] == ["go", "python", "typescript"]
    assert (
        scope["semantic_index"] == "not_qualified"
        and scope["evidence_gate"] == "spring_requestparam_sql_review_v1"
    )
    with pytest.raises(TraceProofError, match="Implemented"):
        adapter_for("rust")


@pytest.mark.parametrize("path", ["pom.xml", "module/build.gradle", "vendor/a.jar", "Main.kt"])
def test_java_profile_rejects_unqualified_project_inputs(path):
    with pytest.raises(TraceProofError, match="dependency-free"):
        validate_extraction_scope(manifest("A.java", path), "java")
    with pytest.raises(TraceProofError, match="no files"):
        validate_extraction_scope(manifest("app.py"), "java")


def test_java_reports_never_inherit_python_readiness(store, scanned):
    repo, run, attempt, _ = scanned
    scope = language_scope(manifest("A.java", "web.ts"), "java")
    with store.transaction() as session:
        record = session.get(ScanAttempt, attempt)
        record.report = {
            **record.report,
            "language": "java",
            "language_scope": scope,
            "execution_complete": True,
            "diagnostic_errors": 0,
            "unmapped_candidates": 0,
        }
    report = publish_report(store, repo, run, attempt)
    assert report["language"] == "java"
    assert report["static_review_readiness"]["state"] == "incomplete"
    assert "java_semantic_index_not_qualified" in report["static_review_readiness"]["reasons"]
    assert "unselected_languages_present" in report["static_review_readiness"]["reasons"]
    assert get_report(store, repo, report["report_id"]) == report
    assert "typescript" in render_report(report, "scan-csv")


def test_batch_skip_is_language_scoped(store, scanned, tmp_path, monkeypatch):
    query = tmp_path / "q.ql"
    query.write_text("// synthetic")
    called = []

    def source(*args):
        called.append(True)
        raise TraceProofError("Java reached source preflight")

    monkeypatch.setattr(pipeline, "verified_source", source)
    with pytest.raises(TraceProofError, match="Java reached"):
        pipeline.scan_run(store, scanned[1], query, skip_existing=True, language="java")
    assert called
    assert (
        pipeline.scan_run(store, scanned[1], query, skip_existing=True)["status"]
        == "skipped_existing_attempt"
    )
