import json
from types import SimpleNamespace

import pytest
from test_slice03 import captured_source as captured_source
from typer.testing import CliRunner

from veriflow import joern, pipeline
from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.joern_pipeline import selected_language
from veriflow.persistence import ScanAttempt


@pytest.mark.parametrize(
    "path,language",
    [
        ("app.py", "python"),
        ("A.java", "java"),
        ("A.cs", "csharp"),
        ("app.js", "javascript"),
        ("app.ts", "typescript"),
        ("main.go", "go"),
        ("main.rs", "rust"),
        ("main.c", "c"),
        ("main.cpp", "cpp"),
    ],
)
def test_auto_profile(path, language):
    manifest = SimpleNamespace(files=[SimpleNamespace(path=path), SimpleNamespace(path="probe.h")])
    assert selected_language(manifest, "auto") == language


def test_mixed_auto_rejected():
    manifest = SimpleNamespace(files=[SimpleNamespace(path=p) for p in ("a.py", "b.go")])
    with pytest.raises(VeriFlowError):
        selected_language(manifest, "auto")


@pytest.mark.parametrize("failed", [False, True])
def test_pipeline_publication_and_engine_aware_skip(
    store, captured_source, tmp_path, monkeypatch, failed
):
    run = captured_source({"app.py": "pass\n"})
    home = tmp_path / "tools"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()
    with store.transaction() as session:
        session.add(
            ScanAttempt(
                id="old-codeql",
                run_id=run,
                created_at="2026-09-01T00:00:00Z",
                report={"scanner": {"engine_id": "codeql"}, "language": "python"},
            )
        )
    seen = []

    def fake(command, root, name, timeout):
        seen.append((name, timeout))
        if failed:
            raise VeriFlowError("synthetic scanner failure")
        if name == "analyze":
            (root / "flows.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2",
                        "engine_id": "joern",
                        "rule_id": joern.PYTHON_RULE,
                        "represented_python_files": ["app.py"],
                        "source_count": 0,
                        "sink_count": 0,
                        "flow_count": 0,
                        "paths": [],
                    }
                )
            )

    monkeypatch.setattr(joern, "stage", fake)
    options = dict(
        engine="joern",
        language="auto",
        joern_home=home,
        extraction_timeout=17,
        query_timeout=29,
        skip_existing=True,
    )
    result = pipeline.scan_run(store, run, **options)
    assert result["status"] == "incomplete"
    assert result["analysis_status"] == ("failed" if failed else "partial")
    assert result["report_id"] and result["model_calls"] == 0
    assert seen == ([("prepare", 17)] if failed else [("prepare", 17), ("analyze", 29)])
    skipped = pipeline.scan_run(store, run, **options)
    assert skipped["status"] == "skipped_existing_attempt"
    assert skipped["attempt_id"] == result["attempt_id"]
    assert skipped["report_id"] is None
    # A different packaged profile must create an attempt rather than reuse the default.
    alternate = pipeline.scan_run(store, run, **options, joern_profile="python-flask-system-v1")
    assert alternate["status"] == "incomplete"
    assert alternate["attempt_id"] != result["attempt_id"]


@pytest.mark.parametrize(
    "options",
    [
        {"queries": "bad.ql"},
        {"language": "unknown"},
        {"ram_mb": 4096},
        {"java_profile": "maven"},
        {"csharp_offline": True},
    ],
)
def test_incompatible_options_rejected_before_scanning(store, options):
    with pytest.raises(VeriFlowError):
        pipeline.scan_run(store, "unused", engine="joern", joern_home="/unused", **options)


def test_cli_joern_routes_without_query(store, monkeypatch):
    def fake(*args, **kwargs):
        assert args[2] is None
        assert kwargs["engine"] == "joern" and kwargs["language"] == "auto"
        return {"status": "incomplete"}

    monkeypatch.setattr(pipeline, "scan_run", fake)
    result = CliRunner().invoke(
        app,
        [
            "--state-dir",
            str(store.root),
            "scan-run",
            "run",
            "--engine",
            "joern",
            "--joern-home",
            "/tools",
            "--language",
            "auto",
        ],
    )
    assert result.exit_code == 0, result.output
