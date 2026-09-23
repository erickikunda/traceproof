from types import SimpleNamespace

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from veriflow import pipeline
from veriflow.domain import VeriFlowError
from veriflow.languages import adapter_for, language_scope, validate_extraction_scope
from veriflow.persistence import ScanAttempt
from veriflow.reports import get_report, publish_report, render_report


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
    with pytest.raises(VeriFlowError, match="Implemented"):
        adapter_for("rust")


@pytest.mark.parametrize("path", ["pom.xml", "module/build.gradle", "vendor/a.jar", "Main.kt"])
def test_java_profile_rejects_unqualified_project_inputs(path):
    with pytest.raises(VeriFlowError, match="dependency-free"):
        validate_extraction_scope(manifest("A.java", path), "java")
    with pytest.raises(VeriFlowError, match="no files"):
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
        raise VeriFlowError("Java reached source preflight")

    monkeypatch.setattr(pipeline, "verified_source", source)
    with pytest.raises(VeriFlowError, match="Java reached"):
        pipeline.scan_run(store, scanned[1], query, skip_existing=True, language="java")
    assert called
    assert (
        pipeline.scan_run(store, scanned[1], query, skip_existing=True)["status"]
        == "skipped_existing_attempt"
    )


def test_source_only_profile_discloses_omitted_inputs():
    scope = validate_extraction_scope(
        manifest("src/A.java", "pom.xml", "build.gradle", "X.kt", "a.jar"), "java", "source-only"
    )
    assert scope["adapter_profile"] == "java-source-only-v1"
    assert scope["omitted_file_count"] == 4
    assert scope["unselected_languages"] == ["kotlin"]
    assert scope["dependency_resolution"] == "not_qualified"
    with pytest.raises(VeriFlowError):
        validate_extraction_scope(manifest("a.py"), "python", "source-only")


def test_skip_existing_does_not_cross_java_profiles(store, scanned, tmp_path, monkeypatch):
    with store.transaction() as session:
        record = session.get(ScanAttempt, scanned[2])
        record.report = {
            **record.report,
            "language": "java",
            "language_scope": {"adapter_profile": "java-source-only-v1"},
        }
    query = tmp_path / "q.ql"
    query.write_text("// query")
    assert (
        pipeline.scan_run(
            store,
            scanned[1],
            query,
            language="java",
            java_profile="source-only",
            skip_existing=True,
        )["status"]
        == "skipped_existing_attempt"
    )

    def reached(*args):
        raise VeriFlowError("Different profile reached preflight")

    monkeypatch.setattr(pipeline, "verified_source", reached)
    with pytest.raises(VeriFlowError, match="Different profile"):
        pipeline.scan_run(store, scanned[1], query, language="java", skip_existing=True)


@pytest.mark.parametrize(
    "paths,expected",
    [
        (["app.py", "README.md"], "python"),
        (["src/C.java", "pom.xml"], "java"),
    ],
)
def test_auto_selects_single_supported_language(paths, expected):
    from veriflow.languages import select_language

    assert select_language(manifest(*paths), "auto") == expected


@pytest.mark.parametrize(
    "paths", [["a.py", "C.java"], ["C.java", "web.ts"], ["main.go"], ["README.md"]]
)
def test_auto_rejects_mixed_unsupported_or_empty_inventory(paths):
    from veriflow.languages import select_language

    with pytest.raises(VeriFlowError, match="Automatic selection"):
        select_language(manifest(*paths), "auto")


def test_auto_skip_resolves_to_existing_language(store, scanned, tmp_path):
    query = tmp_path / "q.ql"
    query.write_text("// query")
    result = pipeline.scan_run(store, scanned[1], query, language="auto", skip_existing=True)
    assert result["status"] == "skipped_existing_attempt"
    assert result["language"] == "python" and result["requested_language"] == "auto"


def test_csharp_selection_and_explicit_scope():
    from veriflow.languages import select_language

    snapshot = manifest("Controllers/Lookup.cs", "App.csproj", "View.cshtml", "dependency.dll")
    assert select_language(snapshot, "auto") == "csharp"
    scope = validate_extraction_scope(snapshot, "csharp")
    assert scope["adapter_profile"] == "csharp-source-only-v1"
    assert scope["omitted_file_count"] == 3 and scope["framework_coverage"] == "not_qualified"
    assert scope["evidence_gate"] == "aspnet_sql_review_v2"


def test_csharp_reports_do_not_inherit_python_readiness(store, scanned):
    repo, run, attempt, _ = scanned
    with store.transaction() as session:
        record = session.get(ScanAttempt, attempt)
        record.report = {
            **record.report,
            "language": "csharp",
            "language_scope": validate_extraction_scope(manifest("C.cs"), "csharp"),
        }
    report = publish_report(store, repo, run, attempt)
    assert report["static_review_readiness"]["state"] == "incomplete"
    assert "csharp_semantic_index_not_qualified" in report["static_review_readiness"]["reasons"]
    assert get_report(store, repo, report["report_id"]) == report


@pytest.mark.parametrize("language,filename", [("javascript", "app.js"), ("typescript", "app.ts")])
def test_js_ts_distinct_scope_and_automatic_selection(language, filename):
    from veriflow.languages import select_language

    snapshot = manifest(filename, "package.json", "tsconfig.json")
    assert select_language(snapshot, "auto") == language
    assert adapter_for(language).extractor == "javascript"
    scope = validate_extraction_scope(snapshot, language)
    assert scope["selected_file_count"] == 1 and scope["omitted_file_count"] == 2
    assert scope["evidence_gate"] == "unsupported"
    assert scope["configuration_files"] == "omitted"
    with pytest.raises(VeriFlowError, match="Automatic selection"):
        select_language(manifest("app.js", "app.ts"), "auto")


@pytest.mark.parametrize("language,filename", [("javascript", "app.js"), ("typescript", "app.ts")])
def test_js_ts_report_readiness_stays_incomplete(store, scanned, language, filename):
    repo, run, attempt, _ = scanned
    with store.transaction() as session:
        record = session.get(ScanAttempt, attempt)
        record.report = {
            **record.report,
            "language": language,
            "language_scope": validate_extraction_scope(manifest(filename), language),
        }
    report = publish_report(store, repo, run, attempt)
    assert report["static_review_readiness"]["state"] == "incomplete"
    assert (
        f"{language}_semantic_index_not_qualified" in report["static_review_readiness"]["reasons"]
    )
