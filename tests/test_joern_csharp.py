import hashlib
import json
from types import SimpleNamespace

import pytest
from test_slice03 import captured_source as captured_source

from veriflow import joern, joern_csharp
from veriflow.domain import TraceProofError
from veriflow.reports import publish_report
from veriflow.scanning import scan_report


def test_whole_ambiguous_path_withheld(tmp_path):
    data = b"class C { void M() { Use(name, name); } }"
    (tmp_path / "A.cs").write_bytes(data)
    selected = [SimpleNamespace(path="A.cs", sha256=hashlib.sha256(data).hexdigest())]
    doc = {"paths": [[{"file": "A.cs", "code": "name", "line": 1}]], "flow_count": 1}
    raw, audit = joern_csharp.map_output(doc, tmp_path, selected)
    assert json.loads(raw)["paths"] == []
    assert audit["unsupported_paths"] == 1
    assert audit["paths"][0]["nodes"][0]["nodes"][0]["status"] == "ambiguous"


def test_invalid_reference_cannot_become_partial_path(tmp_path):
    with pytest.raises(TraceProofError):
        joern_csharp.map_output({"paths": [[{"file": "../A.cs"}]]}, tmp_path, [])


def test_missing_repair_and_artifact_tooling_rejected(store, tmp_path):
    with pytest.raises(TraceProofError):
        joern_csharp.repaired_frontend(store, tmp_path, tmp_path)


def test_csharp_durable_discovery_and_raw_mapping(store, captured_source, tmp_path, monkeypatch):
    run = captured_source(
        {"A.cs": "class C { void Lookup(string name) { Use(name); } }", "x.csproj": "not copied"}
    )
    home = tmp_path / "tool"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()
    monkeypatch.setattr(
        joern_csharp, "repaired_frontend", lambda *a: (["trusted-tool"], {"pinned": True})
    )

    def fake(command, root, name, timeout):
        assert not (root / "source/x.csproj").exists()
        if name == "analyze":
            (root / "flows.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2",
                        "engine_id": "joern",
                        "rule_id": "veriflow/joern-csharp-lookup-commandtext-v1",
                        "represented_csharp_files": ["A.cs"],
                        "source_count": 1,
                        "sink_count": 1,
                        "flow_count": 1,
                        "paths": [[{"file": "A.cs", "line": 0, "code": "string name"}]],
                    }
                )
            )

    monkeypatch.setattr(joern, "stage", fake)
    result = joern.discover(store, run, home, repair_dir=tmp_path)
    fetched = scan_report(store, "example", run, result["attempt_id"])
    assert fetched["candidate_count"] == 1
    assert fetched["status"] == "partial"
    assert result["source_mapping"]["validated_paths"] == 1
    assert result["discovery_coverage"]["selected_csharp_files"] == 1
    assert fetched["execution_complete"] is False
    published = publish_report(store, "example", run, result["attempt_id"])
    assert published["source_mapping"]["validated_paths"] == 1
    assert published["static_review_readiness"]["state"] == "incomplete"


@pytest.mark.parametrize("attribute,expected", [("[FromQuery] ", 1), ("", 0)])
def test_query_source_gate_requires_mapped_fact(tmp_path, attribute, expected):
    data = (
        "using Microsoft.AspNetCore.Mvc;\nclass C {\n"
        f" void Search({attribute}string term) {{ }}\n}}\n"
    ).encode()
    (tmp_path / "A.cs").write_bytes(data)
    selected = [SimpleNamespace(path="A.cs", sha256=hashlib.sha256(data).hexdigest())]
    doc = {"paths": [[{"file": "A.cs", "code": "string term", "line": 3}]], "flow_count": 1}
    raw, audit = joern_csharp.map_output(doc, tmp_path, selected, require_query_source=True)
    assert len(json.loads(raw)["paths"]) == expected
    assert audit["validated_paths"] == expected
    # Legacy syntax-span mapping remains available without the source gate.
    raw, _ = joern_csharp.map_output(doc, tmp_path, selected)
    assert len(json.loads(raw)["paths"]) == 1
