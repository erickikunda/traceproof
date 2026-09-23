import json
from types import SimpleNamespace

import pytest
from test_slice03 import captured_source as captured_source

from veriflow import joern
from veriflow.bundles import build_bundle
from veriflow.claims import bundle_engine, requirements
from veriflow.domain import VeriFlowError
from veriflow.reports import publish_report
from veriflow.scanning import scan_report


def output(file="App.java", line=1):
    return json.dumps(
        {
            "schema_version": "2",
            "represented_java_files": ["App.java"],
            "source_count": 1,
            "sink_count": 1,
            "engine_id": "joern",
            "rule_id": joern.RULE,
            "flow_count": 1,
            "paths": [[{"file": file, "line": line}]],
        }
    ).encode()


@pytest.mark.parametrize(
    "file,line",
    [("../App.java", 1), ("missing.java", 1), ("App.java", 0), ("App.java", True), ("App.java", 3)],
)
def test_invalid_flow_references_rejected(tmp_path, file, line):
    (tmp_path / "App.java").write_text("class App {}\n")
    manifest = SimpleNamespace(files=[SimpleNamespace(path="App.java")])
    with pytest.raises(VeriFlowError):
        joern.to_sarif(output(file, line), tmp_path, manifest)


@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize(
    "language", ["java", "python", "javascript", "typescript", "go", "c", "cpp"]
)
def test_durable_discovery_and_failure(
    store, captured_source, tmp_path, monkeypatch, failed, language
):
    suffix = joern.SUFFIXES[language]
    filename = "App" + (suffix[0] if isinstance(suffix, tuple) else suffix)
    run = captured_source(
        {
            filename: "class App {}\n" if language == "java" else "pass\n",
            "pom.xml": "not copied",
            "go.mod": "module example.com/probe\n",
        }
    )
    home = tmp_path / "joern"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()

    def fake(command, root, name, timeout):
        assert not (root / "source/pom.xml").exists()
        assert (root / "source/go.mod").exists() == (language == "go")
        if failed:
            raise VeriFlowError("stage failed")
        if name == "analyze":
            doc = json.loads(output())
            if language != "java":
                assert command[0].endswith("/joern")
                doc["rule_id"] = (
                    joern.PYTHON_RULE
                    if language == "python"
                    else "veriflow/joern-go-lookup-command-v1"
                    if language == "go"
                    else f"veriflow/joern-{language}-lookup-system-v1"
                    if language in {"c", "cpp"}
                    else f"veriflow/joern-{language}-lookup-eval-v1"
                )
                doc[f"represented_{language}_files"] = [filename]
                doc["paths"][0][0]["file"] = filename
            (root / "flows.json").write_text(json.dumps(doc))

    monkeypatch.setattr(joern, "stage", fake)
    report = joern.discover(store, run, home, language=language)
    retrieved = scan_report(store, "example", run, report["attempt_id"])
    assert retrieved["status"] == ("failed" if failed else "partial")
    assert retrieved["candidate_count"] == (None if failed else 1)
    assert retrieved["scanner"]["engine_id"] == "joern"
    published = publish_report(store, "example", run, report["attempt_id"])
    assert published["static_review_readiness"]["state"] == "incomplete"
    assert published["scanner"]["engine_id"] == "joern"
    assert published["scanner_limitations"]
    if not failed:
        assert retrieved["execution_complete"] is False
        assert retrieved["process_stages_completed"] is True
        assert retrieved["diagnostic_errors"] is None
        assert published["discovery_coverage"]["observation"] == "modeled_flows_found"
        bundle = build_bundle(
            store, report["attempt_id"], retrieved["candidates"][0]["fingerprint"]
        )
        assert bundle_engine(bundle) == "joern"
        assert not requirements(bundle["rule_id"], bundle_engine(bundle))["supported"]


@pytest.mark.parametrize(
    "sources,sinks,flows,observation",
    [
        (1, 1, 1, "modeled_flows_found"),
        (0, 0, 0, "no_modeled_sources_or_sinks"),
        (0, 1, 0, "no_modeled_sources"),
        (1, 0, 0, "no_modeled_sinks"),
        (1, 1, 0, "no_recorded_flow_between_modeled_endpoints"),
    ],
)
def test_coverage_never_implies_parse_completeness(tmp_path, sources, sinks, flows, observation):
    doc = {
        "source_count": sources,
        "sink_count": sinks,
        "flow_count": flows,
        "represented_java_files": ["App.java"],
    }
    selected = [SimpleNamespace(path=p) for p in ("App.java", "Missing.java")]
    result = joern.discovery_coverage(doc, tmp_path, selected)
    assert result["observation"] == observation
    assert result["missing_graph_files"] == ["Missing.java"]
    assert result["parse_completeness_verified"] is False
    assert result["parser_diagnostics"] == "not_qualified"


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_count", True),
        ("sink_count", -1),
        ("flow_count", 0),
        ("represented_java_files", "App.java"),
        ("source_count", 0),
        ("schema_version", "1"),
    ],
)
def test_invalid_coverage_counters_rejected(key, value):
    doc = json.loads(output())
    doc[key] = value
    with pytest.raises(VeriFlowError):
        joern.decode_output(json.dumps(doc).encode())


def test_graph_inventory_cannot_claim_foreign_source(tmp_path):
    doc = {"represented_java_files": ["../App.java"]}
    with pytest.raises(VeriFlowError, match="unexpected source"):
        joern.discovery_coverage(doc, tmp_path, [SimpleNamespace(path="App.java")])


@pytest.mark.parametrize(
    "language,repair", [("unknown", None), ("csharp", None), ("python", "repair")]
)
def test_invalid_profile_combination_rejected(store, language, repair):
    with pytest.raises(VeriFlowError, match="language/repair"):
        joern.discover(store, "unused", "/unused", language=language, repair_dir=repair)
