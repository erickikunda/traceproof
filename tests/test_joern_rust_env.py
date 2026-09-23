import json

import pytest
from test_slice03 import captured_source as captured_source

from veriflow import joern, pipeline
from veriflow.domain import VeriFlowError
from veriflow.scanning import scan_report


@pytest.mark.parametrize("language,extension", [("rust", "rs")])
def test_rust_env_profile_publication_and_retry(
    store, captured_source, tmp_path, monkeypatch, language, extension
):
    filename = f"app.{extension}"
    from test_joern_rust import BASE

    from veriflow import joern_rust

    run = captured_source(
        {filename: "fn main() {}\n", "Cargo.toml": BASE.replace("main.rs", filename)}
    )
    monkeypatch.setattr(joern_rust, "trusted_toolchain", lambda *a: tmp_path)
    home = tmp_path / "tools"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()

    def fake(command, root, name, timeout, **kwargs):
        if name == "analyze":
            (root / "flows.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2",
                        "engine_id": "joern",
                        "rule_id": "veriflow/joern-rust-env-shell-v1",
                        f"represented_{language}_files": [filename],
                        "source_count": 1,
                        "sink_count": 1,
                        "flow_count": 1,
                        "paths": [[{"file": filename, "line": 1, "code": "value"}]],
                    }
                )
            )

    monkeypatch.setattr(joern, "stage", fake)
    options = dict(
        engine="joern",
        language="auto",
        joern_home=home,
        rust_home=tmp_path,
        joern_profile="rust-env-shell-v1",
        skip_existing=True,
    )
    result = pipeline.scan_run(store, run, **options)
    assert result["status"] == "incomplete" and result["analysis_status"] == "partial"
    assert result["model_calls"] == 0 and result["report_id"]
    report = scan_report(store, "example", run, result["attempt_id"])
    assert report["candidate_count"] == 1 and not report["execution_complete"]
    assert report["discovery_profile"] == "rust-env-shell-v1"
    assert pipeline.scan_run(store, run, **options)["status"] == "skipped_existing_attempt"


@pytest.mark.parametrize("language", ["python", "java", "javascript", "c"])
def test_rust_env_rejects_other_languages(store, language):
    with pytest.raises(VeriFlowError, match="profile/language"):
        joern.discover(
            store,
            "unused",
            "/unused",
            language=language,
            discovery_profile="rust-env-shell-v1",
        )
