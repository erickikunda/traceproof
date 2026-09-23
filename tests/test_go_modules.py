import json

import pytest
from test_dependency_discovery import properties_of
from test_dependency_discovery import snapshot as snapshot

from veriflow.sbom_export import export_sbom

BASIC = """module github.com/example/app

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	golang.org/x/crypto v0.14.0 // indirect
)

require github.com/other/pkg v1.2.3
"""


def libraries(store, repo, snapshot_id, **options):
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, **options))
    return {c["purl"]: c for c in document["components"] if c["type"] == "library"}


def coverage_of(store, repo, snapshot_id, **options):
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, **options))
    return {p["name"]: p["value"] for p in document["metadata"]["properties"]}


def test_block_and_single_requirements_are_read(store, snapshot):
    repo, snapshot_id = snapshot({"go.mod": BASIC})
    found = libraries(store, repo, snapshot_id)
    assert set(found) == {
        "pkg:golang/github.com/gin-gonic/gin@v1.9.1",
        "pkg:golang/golang.org/x/crypto@v0.14.0",
        "pkg:golang/github.com/other/pkg@v1.2.3",
    }
    gin = found["pkg:golang/github.com/gin-gonic/gin@v1.9.1"]
    assert gin["group"] == "github.com/gin-gonic" and gin["name"] == "gin"
    assert gin["version"] == "v1.9.1"
    # Go has no lockfile; go.mod states a version, it does not pin a build.
    assert properties_of(gin)["veriflow:resolution"] == "declared_version"


def test_indirect_requirements_are_marked_not_dropped(store, snapshot):
    repo, snapshot_id = snapshot({"go.mod": BASIC})
    found = libraries(store, repo, snapshot_id)
    crypto = properties_of(found["pkg:golang/golang.org/x/crypto@v0.14.0"])
    assert crypto["veriflow:declared_scopes"] == "indirect"
    gin = properties_of(found["pkg:golang/github.com/gin-gonic/gin@v1.9.1"])
    assert gin["veriflow:declared_scopes"] == "direct"
    notes = coverage_of(store, repo, snapshot_id)["veriflow:ecosystem_notes"]
    assert "go_indirect_requirements=1" in notes
    # Reading a recorded indirect entry is not resolving a closure.
    assert coverage_of(store, repo, snapshot_id)["veriflow:inheritance_resolved"] == "false"


def test_replaced_module_never_carries_its_declared_version(store, snapshot):
    source = (
        "module github.com/example/app\n"
        "require github.com/old/pkg v1.0.0\n"
        "replace github.com/old/pkg => github.com/new/pkg v2.0.0\n"
    )
    repo, snapshot_id = snapshot({"go.mod": source})
    found = libraries(store, repo, snapshot_id)
    old = found["pkg:golang/github.com/old/pkg"]
    # A replaced requirement is not what a build resolves.
    assert "version" not in old
    assert properties_of(old)["veriflow:resolution"] == "replaced"
    target = found["pkg:golang/github.com/new/pkg@v2.0.0"]
    assert properties_of(target)["veriflow:version_source"] == "replacement_target"
    assert properties_of(target)["veriflow:declared_scopes"] == "replacement"
    assert (
        "go_replaced_requirements=1"
        in coverage_of(store, repo, snapshot_id)["veriflow:ecosystem_notes"]
    )


def test_version_specific_replacement_only_applies_to_that_version(store, snapshot):
    source = (
        "module github.com/example/app\n"
        "require github.com/a/b v1.0.0\n"
        "require github.com/c/d v3.0.0\n"
        "replace github.com/a/b v1.0.0 => github.com/a/b v1.0.1\n"
        "replace github.com/c/d v9.9.9 => github.com/c/d v9.9.10\n"
    )
    repo, snapshot_id = snapshot({"go.mod": source})
    found = libraries(store, repo, snapshot_id)
    assert "pkg:golang/github.com/a/b" in found
    # The replacement names a version this module does not require, so nothing is replaced.
    assert "pkg:golang/github.com/c/d@v3.0.0" in found


def test_local_replacement_yields_no_registry_component(store, snapshot):
    source = (
        "module github.com/example/app\n"
        "require github.com/old/pkg v1.0.0\n"
        "replace github.com/old/pkg => ./vendored/pkg\n"
    )
    repo, snapshot_id = snapshot({"go.mod": source})
    found = libraries(store, repo, snapshot_id)
    assert properties_of(found["pkg:golang/github.com/old/pkg"])["veriflow:resolution"] == (
        "replaced"
    )
    assert not any("vendored" in purl for purl in found)
    notes = coverage_of(store, repo, snapshot_id)["veriflow:ecosystem_notes"]
    assert "go_local_replacements=1" in notes


def test_replace_block_form_is_read(store, snapshot):
    source = (
        "module github.com/example/app\n"
        "require github.com/old/pkg v1.0.0\n"
        "replace (\n\tgithub.com/old/pkg => github.com/new/pkg v2.0.0\n)\n"
    )
    repo, snapshot_id = snapshot({"go.mod": source})
    found = libraries(store, repo, snapshot_id)
    assert "pkg:golang/github.com/new/pkg@v2.0.0" in found
    assert "version" not in found["pkg:golang/github.com/old/pkg"]


def test_excluded_versions_are_counted_not_emitted(store, snapshot):
    source = (
        "module github.com/example/app\n"
        "require github.com/a/b v1.0.0\n"
        "exclude github.com/bad/pkg v0.1.0\n"
    )
    repo, snapshot_id = snapshot({"go.mod": source})
    found = libraries(store, repo, snapshot_id)
    assert not any("bad" in purl for purl in found)
    assert (
        "go_excluded_versions=1"
        in coverage_of(store, repo, snapshot_id)["veriflow:ecosystem_notes"]
    )


@pytest.mark.parametrize(
    "version",
    ["v0.0.0-20210101000000-abcdef123456", "v2.0.0+incompatible", "v1.2.3-rc.1"],
)
def test_pseudo_and_qualified_versions_are_accepted(store, snapshot, version):
    repo, snapshot_id = snapshot(
        {"go.mod": f"module github.com/example/app\nrequire github.com/a/b {version}\n"}
    )
    assert f"pkg:golang/github.com/a/b@{version}" in libraries(store, repo, snapshot_id)


@pytest.mark.parametrize(
    "line",
    [
        "require github.com/a/b 1.0.0",
        "require github.com/a/b",
        "require ../escape/pkg v1.0.0",
        "require github.com/a/../b v1.0.0",
    ],
)
def test_malformed_requirements_are_not_emitted(store, snapshot, line):
    repo, snapshot_id = snapshot({"go.mod": f"module github.com/example/app\n{line}\n"})
    assert libraries(store, repo, snapshot_id) == {}


def test_comments_do_not_become_requirements(store, snapshot):
    source = (
        "module github.com/example/app\n"
        "// require github.com/commented/pkg v1.0.0\n"
        "require github.com/real/pkg v1.0.0 // some note\n"
    )
    repo, snapshot_id = snapshot({"go.mod": source})
    found = libraries(store, repo, snapshot_id)
    assert set(found) == {"pkg:golang/github.com/real/pkg@v1.0.0"}
    assert (
        properties_of(found["pkg:golang/github.com/real/pkg@v1.0.0"])["veriflow:declared_scopes"]
        == "direct"
    )


def test_vendored_go_mod_is_ignored(store, snapshot):
    repo, snapshot_id = snapshot(
        {"go.mod": BASIC, "vendor/github.com/x/y/go.mod": "module github.com/x/y\n"}
    )
    coverage = coverage_of(store, repo, snapshot_id)
    assert coverage["veriflow:excluded_declarations_ignored"] == "1"
    assert coverage["veriflow:dependency_files_parsed"] == "go=1"


def test_go_import_evidence_is_exact(store, snapshot):
    source = (
        'package main\n\nimport (\n\t"fmt"\n\t"github.com/gin-gonic/gin/binding"\n)\n\n'
        'import "github.com/other/pkg"\n'
    )
    repo, snapshot_id = snapshot({"go.mod": BASIC, "main.go": source})
    found = libraries(store, repo, snapshot_id, usage=True)
    gin = properties_of(found["pkg:golang/github.com/gin-gonic/gin@v1.9.1"])
    # A package below the module path is still that module.
    assert gin["veriflow:usage_state"] == "import_observed"
    assert gin["veriflow:usage_basis"] == "module_path_exact"
    other = properties_of(found["pkg:golang/github.com/other/pkg@v1.2.3"])
    assert other["veriflow:usage_state"] == "import_observed"
    crypto = properties_of(found["pkg:golang/golang.org/x/crypto@v0.14.0"])
    assert crypto["veriflow:usage_state"] == "not_observed"


def test_go_prefix_match_does_not_cross_a_path_boundary(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "go.mod": "module github.com/example/app\nrequire github.com/a/b v1.0.0\n",
            "main.go": 'package main\nimport "github.com/a/bc"\n',
        }
    )
    found = libraries(store, repo, snapshot_id, usage=True)
    assert properties_of(found["pkg:golang/github.com/a/b@v1.0.0"])["veriflow:usage_state"] == (
        "not_observed"
    )


def test_go_determinism(store, snapshot):
    repo, snapshot_id = snapshot({"go.mod": BASIC, "main.go": 'package main\nimport "fmt"\n'})
    first = export_sbom(store, repo, snapshot_id, packages=True, usage=True)
    assert first == export_sbom(store, repo, snapshot_id, packages=True, usage=True)
