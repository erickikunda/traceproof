import json

import pytest
from test_dependency_discovery import properties_of
from test_dependency_discovery import snapshot as snapshot

from veriflow.dependency_usage import npm_package, npm_specifiers
from veriflow.domain import VeriFlowError
from veriflow.sbom_export import export_sbom

LOCK = {
    "lockfileVersion": 3,
    "packages": {
        "": {"name": "app"},
        "node_modules/lodash": {"version": "4.17.20"},
        "node_modules/left-pad": {"version": "1.3.0"},
        "node_modules/@scope/widget": {"version": "2.0.0"},
    },
}
POM = (
    '<project xmlns="http://maven.apache.org/POM/4.0.0">'
    "<groupId>com.example</groupId><artifactId>app</artifactId>"
    "<dependencies>"
    "<dependency><groupId>org.springframework</groupId>"
    "<artifactId>spring-web</artifactId><version>5.3.9</version></dependency>"
    "<dependency><groupId>junit</groupId>"
    "<artifactId>junit</artifactId><version>4.13.2</version></dependency>"
    "</dependencies></project>"
)


def usage_of(store, repo, snapshot_id):
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, usage=True))
    states = {}
    for component in document["components"]:
        if component["type"] == "library":
            states[component["purl"]] = properties_of(component).get("veriflow:usage_state")
    return states, {p["name"]: p["value"] for p in document["metadata"]["properties"]}


@pytest.mark.parametrize(
    "specifier,expected",
    [
        ("lodash", "lodash"),
        ("lodash/fp", "lodash"),
        ("@scope/widget", "@scope/widget"),
        ("@scope/widget/sub", "@scope/widget"),
        ("LoDash", "lodash"),
        ("./local", None),
        ("../up", None),
        ("/abs", None),
        ("node:fs", None),
        ("https://cdn.example/x.js", None),
        ("@scope", None),
    ],
)
def test_specifier_reduces_to_a_package_name(specifier, expected):
    assert npm_package(specifier) == expected


@pytest.mark.parametrize(
    "source",
    [
        'const a = require("lodash");',
        "import a from 'lodash';",
        'import { map } from "lodash/fp";',
        'const a = await import("lodash");',
        'export { x } from "lodash";',
        'import "lodash";',
    ],
)
def test_import_forms_are_recognized(source):
    assert "lodash" in npm_specifiers(source)


def test_observed_import_is_evidence(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "package-lock.json": LOCK,
            "src/app.js": 'const _ = require("lodash");\nimport w from "@scope/widget";\n',
        }
    )
    states, properties = usage_of(store, repo, snapshot_id)
    assert states["pkg:npm/lodash@4.17.20"] == "import_observed"
    assert states["pkg:npm/%40scope/widget@2.0.0"] == "import_observed"
    assert states["pkg:npm/left-pad@1.3.0"] == "not_observed"
    assert properties["veriflow:usage_analysis"] == "import evidence only; not reachability"
    assert properties["veriflow:usage_call_graph_resolved"] == "false"
    assert properties["veriflow:usage_vulnerable_symbol_matching"] == "none"


def test_absent_import_never_reads_as_unused(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK, "src/app.js": "const x = 1;\n"})
    states, properties = usage_of(store, repo, snapshot_id)
    # The state names what was observed, not a conclusion about use.
    assert set(states.values()) == {"not_observed"}
    assert "not_observed=3" in properties["veriflow:usage_states"]
    assert "unused" not in json.dumps(states)


def test_no_source_of_the_language_is_not_evaluated(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK, "README.md": "hello\n"})
    states, properties = usage_of(store, repo, snapshot_id)
    assert set(states.values()) == {"not_evaluated"}
    assert "not_evaluated=3" in properties["veriflow:usage_states"]


def test_vendored_and_bundled_sources_are_excluded(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "package-lock.json": LOCK,
            "node_modules/other/index.js": 'require("lodash");',
            "dist/app.bundle.js": 'require("left-pad");',
            "src/app.min.js": 'require("left-pad");',
            "src/app.js": 'require("lodash");',
        }
    )
    states, properties = usage_of(store, repo, snapshot_id)
    assert states["pkg:npm/lodash@4.17.20"] == "import_observed"
    # A bundle inlines its dependencies and would report everything as imported.
    assert states["pkg:npm/left-pad@1.3.0"] == "not_observed"
    assert properties["veriflow:usage_files_scanned"] == "npm=1"


def test_maven_group_prefix_is_conventional(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": POM,
            "src/App.java": (
                "package com.example;\n"
                "import org.springframework.web.client.RestTemplate;\n"
                "import org.junit.Test;\n"
            ),
        }
    )
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, usage=True))
    found = {c["purl"]: c for c in document["components"] if c["type"] == "library"}
    spring = properties_of(found["pkg:maven/org.springframework/spring-web@5.3.9"])
    assert spring["veriflow:usage_state"] == "import_observed"
    assert spring["veriflow:usage_basis"] == "group_prefix_conventional"
    # junit's groupId is "junit" but its package is org.junit; the convention does not hold.
    junit = properties_of(found["pkg:maven/junit/junit@4.13.2"])
    assert junit["veriflow:usage_state"] == "not_observed"
    assert "veriflow:usage_basis" not in junit


def test_static_and_wildcard_java_imports_are_read(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": POM,
            "src/App.java": (
                "import static org.springframework.util.Assert.notNull;\n"
                "import org.springframework.web.*;\n"
            ),
        }
    )
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, usage=True))
    found = {c["purl"]: c for c in document["components"] if c["type"] == "library"}
    spring = properties_of(found["pkg:maven/org.springframework/spring-web@5.3.9"])
    assert spring["veriflow:usage_state"] == "import_observed"


def test_usage_is_opt_in_and_requires_packages(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK, "src/app.js": 'require("lodash");'})
    default = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    assert all(
        "veriflow:usage_state" not in properties_of(c)
        for c in default["components"]
        if c["type"] == "library"
    )
    with pytest.raises(VeriFlowError, match="requires --packages"):
        export_sbom(store, repo, snapshot_id, usage=True)


def test_usage_export_is_deterministic(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK, "src/app.js": 'require("lodash");'})
    first = export_sbom(store, repo, snapshot_id, packages=True, usage=True)
    assert first == export_sbom(store, repo, snapshot_id, packages=True, usage=True)


def test_unreadable_source_is_skipped_and_counted(store, snapshot):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK, "src/app.js": b"\xff\xfe not utf-8"})
    _, properties = usage_of(store, repo, snapshot_id)
    assert "npm:not_utf8=1" in properties["veriflow:usage_files_skipped"]


def test_oversized_source_is_skipped(store, snapshot, monkeypatch):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK, "src/app.js": 'require("lodash");'})
    monkeypatch.setattr("veriflow.dependency_usage.MAX_SOURCE_BYTES", 1)
    states, properties = usage_of(store, repo, snapshot_id)
    assert "npm:oversized=1" in properties["veriflow:usage_files_skipped"]
    # Nothing was read, so nothing can be said about use.
    assert set(states.values()) == {"not_evaluated"}
