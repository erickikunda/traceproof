import json

import pytest
from test_dependency_discovery import snapshot as snapshot
from test_osv_matching import database as database

from traceproof.go_symbols import default_identifier, import_bindings
from traceproof.osv_export import export_osv
from traceproof.sbom_export import export_sbom

MODULE = "github.com/gin-gonic/gin"
GOMOD = f"module github.com/example/app\nrequire {MODULE} v1.9.1\n"


def advisory(identifier="GO-2023-0001", path=MODULE, symbols=("Parse",), **extra):
    entry = {
        "package": {"ecosystem": "Go", "name": MODULE},
        "versions": ["v1.9.1"],
        "ecosystem_specific": {"imports": [{"path": path, "symbols": list(symbols), **extra}]},
    }
    return {"id": identifier, "aliases": [], "affected": [entry]}


def plain_advisory(identifier="GO-2023-0002"):
    return {
        "id": identifier,
        "aliases": [],
        "affected": [{"package": {"ecosystem": "Go", "name": MODULE}, "versions": ["v1.9.1"]}],
    }


def evidence_of(store, repo, snapshot_id, path):
    document = json.loads(
        export_sbom(store, repo, snapshot_id, packages=True, database=path, usage=True)
    )
    found = document["vulnerabilities"]
    properties = {p["name"]: p["value"] for p in found[0]["properties"]} if found else {}
    coverage = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    return found, properties, coverage


@pytest.mark.parametrize(
    "path,expected",
    [
        ("github.com/gin-gonic/gin", "gin"),
        ("github.com/a/b/v2", "b"),
        ("gopkg.in/yaml.v3", "yaml"),
        ("google.golang.org/grpc", "grpc"),
        ("github.com/go-redis/redis/v8", "redis"),
    ],
)
def test_default_identifier_follows_convention(path, expected):
    assert default_identifier(path) == expected


def test_import_bindings_capture_aliases():
    source = (
        'package main\n\nimport (\n\t"fmt"\n\tg "github.com/gin-gonic/gin"\n'
        '\t_ "github.com/side/effect"\n\t. "github.com/dotted/pkg"\n)\n'
    )
    bindings, dotted = import_bindings(source)
    assert bindings["g"] == {"github.com/gin-gonic/gin"}
    assert bindings["fmt"] == {"fmt"}
    # A blank import binds no name and a dot import binds nothing nameable.
    assert bindings[None] >= {"github.com/side/effect", "github.com/dotted/pkg"}
    assert dotted == 1


def test_referenced_symbol_is_evidence(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    found, properties, coverage = evidence_of(store, repo, snapshot_id, database([advisory()]))
    assert properties["traceproof:go_symbol_evidence"] == "symbol_referenced"
    assert properties["traceproof:go_symbols_referenced"] == "Parse"
    # Evidence prioritizes; it never adjudicates.
    assert found[0]["analysis"]["state"] == "in_triage"
    assert coverage["traceproof:go_symbol_analysis"] == (
        "package and symbol references; not reachability"
    )


def test_aliased_import_is_resolved(store, snapshot, database):
    source = f'package main\n\nimport g "{MODULE}"\n\nfunc main() {{ g.Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    _, properties, _ = evidence_of(store, repo, snapshot_id, database([advisory()]))
    assert properties["traceproof:go_symbol_evidence"] == "symbol_referenced"


def test_method_symbol_is_searched_by_its_receiver(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ var d gin.Decoder; _ = d }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    _, properties, _ = evidence_of(
        store, repo, snapshot_id, database([advisory(symbols=("Decoder.Decode",))])
    )
    assert properties["traceproof:go_symbol_evidence"] == "symbol_referenced"
    assert properties["traceproof:go_symbols_referenced"] == "Decoder.Decode"


def test_imported_without_the_named_symbol(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.Other() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    _, properties, _ = evidence_of(store, repo, snapshot_id, database([advisory()]))
    assert properties["traceproof:go_symbol_evidence"] == "package_imported"
    assert "traceproof:go_symbols_referenced" not in properties


def test_vulnerable_package_not_imported_is_not_a_safety_conclusion(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}/binding"\n\nfunc main() {{ binding.X() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    found, properties, _ = evidence_of(
        store, repo, snapshot_id, database([advisory(path=f"{MODULE}/render")])
    )
    assert properties["traceproof:go_symbol_evidence"] == "package_not_imported"
    # The candidate survives unchanged; only its priority differs.
    assert found[0]["analysis"]["state"] == "in_triage"
    assert [v["id"] for v in found] == ["GO-2023-0001"]


def test_advisory_without_symbol_data_is_named_as_such(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    _, properties, coverage = evidence_of(store, repo, snapshot_id, database([plain_advisory()]))
    assert properties["traceproof:go_symbol_evidence"] == "no_symbol_data"
    assert coverage["traceproof:go_advisories_with_symbol_data"] == "0"


def test_no_go_source_is_not_evaluated(store, snapshot, database):
    repo, snapshot_id = snapshot({"go.mod": GOMOD})
    _, properties, _ = evidence_of(store, repo, snapshot_id, database([advisory()]))
    assert properties["traceproof:go_symbol_evidence"] == "not_evaluated"


def test_blank_import_yields_no_symbol_reference(store, snapshot, database):
    source = f'package main\n\nimport _ "{MODULE}"\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    _, properties, _ = evidence_of(store, repo, snapshot_id, database([advisory()]))
    assert properties["traceproof:go_symbol_evidence"] == "package_imported"


def test_dot_imports_are_counted_as_unresolvable(store, snapshot, database):
    source = f'package main\n\nimport (\n\t. "{MODULE}"\n)\n\nfunc main() {{ Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    _, properties, coverage = evidence_of(store, repo, snapshot_id, database([advisory()]))
    # Symbols are in scope unqualified, so no reference is nameable.
    assert properties["traceproof:go_symbol_evidence"] == "package_imported"
    assert coverage["traceproof:go_dot_imports_unresolvable"] == "1"


def test_symbol_match_does_not_cross_an_identifier_boundary(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.ParseAll() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    _, properties, _ = evidence_of(store, repo, snapshot_id, database([advisory()]))
    assert properties["traceproof:go_symbol_evidence"] == "package_imported"


def test_platform_constraints_are_recorded_not_applied(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    path = database([advisory(goos=["windows"], goarch=["arm"])])
    _, properties, coverage = evidence_of(store, repo, snapshot_id, path)
    # The target platform is unknown, so a constraint narrows nothing.
    assert properties["traceproof:go_symbol_evidence"] == "symbol_referenced"
    assert coverage["traceproof:go_platform_filtering"] == "none"


def test_non_go_ecosystems_get_no_symbol_evidence(store, snapshot, database):
    lock = {"lockfileVersion": 3, "packages": {"": {}, "node_modules/lodash": {"version": "1.0.0"}}}
    npm = {
        "id": "GHSA-npm",
        "aliases": [],
        "affected": [{"package": {"ecosystem": "npm", "name": "lodash"}, "versions": ["1.0.0"]}],
    }
    repo, snapshot_id = snapshot({"package-lock.json": lock, "src/a.js": 'require("lodash");'})
    found, properties, _ = evidence_of(store, repo, snapshot_id, database([npm]))
    assert [v["id"] for v in found] == ["GHSA-npm"]
    assert "traceproof:go_symbol_evidence" not in properties


def test_osv_export_carries_symbol_evidence_and_its_limits(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    path = database([advisory()])
    document = json.loads(export_osv(store, repo, snapshot_id, path, usage=True))
    package = document["results"][0]["packages"][0]
    carried = package["vulnerabilities"][0]["traceproof"]
    assert carried["symbol_evidence"] == "symbol_referenced"
    assert carried["symbols_referenced"] == ["Parse"]
    coverage = document["traceproof"]["go_symbol_coverage"]
    assert coverage["call_graph_resolved"] is False
    assert coverage["third_party_source_available"] is False
    assert any("unaffected" in line for line in document["traceproof"]["limitations"])


def test_symbol_evidence_is_deterministic(store, snapshot, database):
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    path = database([advisory()])
    first = export_sbom(store, repo, snapshot_id, packages=True, database=path, usage=True)
    assert first == export_sbom(store, repo, snapshot_id, packages=True, database=path, usage=True)


def test_osv_export_names_a_go_module_with_its_path(store, snapshot, database):
    # Maven writes group:artifact; a Go module path is not a colon-separated name.
    source = f'package main\n\nimport "{MODULE}"\n\nfunc main() {{ gin.Parse() }}\n'
    repo, snapshot_id = snapshot({"go.mod": GOMOD, "main.go": source})
    document = json.loads(export_osv(store, repo, snapshot_id, database([advisory()])))
    package = document["results"][0]["packages"][0]["package"]
    assert package["name"] == MODULE
    assert package["ecosystem"] == "go"
    assert package["purl"] == f"pkg:golang/{MODULE}@v1.9.1"
