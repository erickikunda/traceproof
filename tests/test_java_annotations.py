import zipfile

from test_indexing import captured

from veriflow.java_index import build_java_index, framework_observations
from veriflow.java_parser import parse
from veriflow.persistence import exclusive_worker

SOURCE = b"""import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
class Controller {
    // @RequestBody String fake
    String text = "@PathVariable";
    @GetMapping("/lookup")
    String lookup(@RequestParam String query) { return query; }
}"""


def observations(source):
    result = parse(source)
    assert result["status"] == "parsed"
    return framework_observations([{**result, "path": "C.java", "sha256": "pinned"}])


def test_imports_targets_and_lookalikes():
    result = observations(SOURCE)
    assert result["total"] == 2
    mapping, parameter = result["items"]
    assert mapping["target_kind"] == "method_declaration"
    assert mapping["target_name"] == "lookup" and mapping["line"] == 6
    assert parameter["target_kind"] == "formal_parameter"
    assert parameter["target_name"] == "query"
    assert all(a["spring_namespace_hint"] for a in result["items"])
    assert all(not a["binding_proven"] and not a["request_binding_proven"] for a in result["items"])


def test_unknown_wildcard_and_foreign_imports_are_not_spring_hints():
    for prefix in [
        b"",
        b"import other.GetMapping;",
        b"import org.springframework.web.bind.annotation.*;",
    ]:
        result = observations(prefix + b"class C { @GetMapping void x() {} }")
        assert result["total"] == 1
        assert not result["items"][0]["spring_namespace_hint"]


def test_qualified_syntax_and_shadowing_never_prove_binding():
    source = b"""class C {
        @interface RequestBody {}
        @org.springframework.web.bind.annotation.GetMapping void x(@RequestBody String q) {}
    }"""
    result = observations(source)
    assert result["items"][0]["name_evidence"] == "qualified_syntax"
    assert not result["items"][1]["spring_namespace_hint"]
    assert not result["reachability_proven"]


def test_observation_cap_discloses_truncation():
    result = observations(b"class C {" + b"@RequestBody " * 201 + b"String value; }")
    assert result["total"] == 201 and len(result["items"]) == 200
    assert result["truncated"]


def test_snapshot_report_retains_annotation_evidence(store, archive, manifest):
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("Controller.java", SOURCE)
    run = captured(store, archive, manifest)
    with exclusive_worker(store.root):
        result = build_java_index(store, run)
    assert result["annotation_count"] == 2
    assert result["framework_observations"]["items"][0]["path"] == "Controller.java"
    assert len(result["framework_observations"]["items"][0]["sha256"]) == 64
    assert result["semantic_resolution"] == "not_qualified"
