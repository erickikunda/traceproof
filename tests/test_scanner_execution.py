"""Failure paths must never masquerade as an empty successful scan."""

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from veriflow.codeql_scanner import execute
from veriflow.scanner import ExecutionRequest


@pytest.mark.parametrize("available", [False, True])
def test_missing_or_unlaunchable_scanner(tmp_path, monkeypatch, available):
    monkeypatch.setattr(
        "veriflow.codeql_scanner.shutil.which",
        lambda _: str(tmp_path / "missing-executable") if available else None,
    )
    result = execute(ExecutionRequest(tmp_path / "db", tmp_path / "rules.ql", tmp_path, 1, 2, 2048))
    assert result.status == ("launch_failed" if available else "unavailable")
    assert result.exit_code is None
    assert result.version == ("unknown" if available else None)
    assert not result.output_path.exists()
    assert result.log_path.exists() is available


def test_unknown_backend_rejected_before_store_access():
    from veriflow.domain import VeriFlowError
    from veriflow.pipeline import scan_run
    from veriflow.scanning import analyze

    for operation in (scan_run, analyze):
        with pytest.raises(VeriFlowError, match="not implemented"):
            operation(None, "unused", "unused", engine="unimplemented")


def test_different_engine_does_not_skip_codeql(store, scanned, tmp_path, monkeypatch):
    from veriflow import pipeline
    from veriflow.persistence import ScanAttempt

    with store.transaction() as session:
        attempt = session.get(ScanAttempt, scanned[2])
        attempt.report = {**attempt.report, "scanner": {"engine_id": "joern"}}
    query = tmp_path / "query.ql"
    query.write_text("// fixture")
    monkeypatch.setattr(pipeline, "build_index", lambda *a: {"python_index_gate": "blocked"})
    result = pipeline.scan_run(store, scanned[1], query, skip_existing=True)
    assert result["status"] == "blocked"
    assert result["stopped_after"] == "index"


@pytest.mark.parametrize("engine", ["joern", "opengrep", "unknown", None])
def test_codeql_rule_name_cannot_qualify_other_engine(engine):
    from types import SimpleNamespace

    from veriflow.claims import assess_evidence, requirements

    bundle = {"rule_id": "py/code-injection", "status": "ready", "engine_id": engine}
    assert requirements(bundle["rule_id"], engine)["supported"] is False
    assert requirements(bundle["rule_id"], engine)["policy"] is None
    result = assess_evidence(bundle, SimpleNamespace(verdict="needs_review"))
    assert result["status"] == "unsupported_engine"
    assert result["passed"] is False


def test_new_bundle_without_identity_is_not_legacy():
    from veriflow.claims import bundle_engine

    assert bundle_engine({"builder_version": "5"}) == "codeql"
    assert bundle_engine({"builder_version": "6"}) == "unknown"
    assert bundle_engine({"builder_version": "5", "engine_id": "joern"}) == "joern"
