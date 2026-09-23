import json

import pytest
from test_slice03 import captured_source as captured_source

from veriflow import joern, pipeline
from veriflow.domain import TraceProofError
from veriflow.scanning import scan_report


@pytest.mark.parametrize("language,extension", [("c", "c"), ("cpp", "cpp")])
def test_argv_profile_publication_and_retry(
    store, captured_source, tmp_path, monkeypatch, language, extension
):
    filename = f"app.{extension}"
    run = captured_source({filename: "int main() { return 0; }\n"})
    home = tmp_path / "tools"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()

    def fake(command, root, name, timeout):
        if name == "analyze":
            (root / "flows.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2",
                        "engine_id": "joern",
                        "rule_id": f"veriflow/joern-{language}-argv-system-v1",
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
        joern_profile="c-family-argv-system-v1",
        skip_existing=True,
    )
    result = pipeline.scan_run(store, run, **options)
    assert result["status"] == "incomplete" and result["analysis_status"] == "partial"
    assert result["model_calls"] == 0 and result["report_id"]
    report = scan_report(store, "example", run, result["attempt_id"])
    assert report["candidate_count"] == 1 and not report["execution_complete"]
    assert report["discovery_profile"] == "c-family-argv-system-v1"
    assert pipeline.scan_run(store, run, **options)["status"] == "skipped_existing_attempt"


@pytest.mark.parametrize("language", ["python", "java", "go", "javascript"])
def test_argv_rejects_other_languages(store, language):
    with pytest.raises(TraceProofError, match="profile/language"):
        joern.discover(
            store,
            "unused",
            "/unused",
            language=language,
            discovery_profile="c-family-argv-system-v1",
        )
