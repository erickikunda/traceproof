import hashlib
import json

import pytest
from test_dependency_discovery import snapshot as snapshot
from typer.testing import CliRunner

from veriflow.bundles import canonical
from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.osv_export import export_osv
from veriflow.osv_matching import semver_key
from veriflow.sbom_export import export_sbom

LOCK = {
    "lockfileVersion": 3,
    "packages": {
        "": {"name": "app"},
        "node_modules/lodash": {"version": "4.17.20"},
        "node_modules/left-pad": {"version": "1.3.0"},
    },
}


POM = (
    '<project xmlns="http://maven.apache.org/POM/4.0.0">'
    "<groupId>com.example</groupId><artifactId>app</artifactId>"
    "<dependencies><dependency>"
    "<groupId>org.springframework</groupId><artifactId>spring-web</artifactId>"
    "<version>5.3.9</version>"
    "</dependency></dependencies></project>"
)


def osv(identifier, ecosystem, name, **affected):
    return {
        "id": identifier,
        "aliases": ["CVE-2020-0001"],
        "summary": "Synthetic advisory",
        "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L"}],
        "affected": [{"package": {"ecosystem": ecosystem, "name": name}, **affected}],
    }


def semver_range(introduced, fixed=None, last_affected=None):
    events = [{"introduced": introduced}]
    if fixed:
        events.append({"fixed": fixed})
    if last_affected:
        events.append({"last_affected": last_affected})
    return {"ranges": [{"type": "SEMVER", "events": events}]}


@pytest.fixture
def database(tmp_path):
    def make(records, output="osv", raw_files=None, **overrides):
        root = tmp_path / output
        (root / "records").mkdir(parents=True, exist_ok=True)
        listing = {}
        for record in records:
            path = root / "records" / f"{record['id']}.json"
            raw = json.dumps(record).encode()
            path.write_bytes(raw)
            listing[f"{record['id']}.json"] = hashlib.sha256(raw).hexdigest()
        for name, raw in (raw_files or {}).items():
            (root / "records" / name).write_bytes(raw)
            listing[name] = hashlib.sha256(raw).hexdigest()
        profile = {
            "version": "1",
            "source": "https://osv.example.invalid/",
            "exported_at": "2026-09-01T00:00:00Z",
            "ecosystems": ["npm", "Maven", "Go"],
            "records_directory": "records",
            "record_count": len(listing),
            "inventory_sha256": hashlib.sha256(canonical(listing)).hexdigest(),
            **overrides,
        }
        path = root / "osv-profile.json"
        path.write_text(json.dumps(profile))
        return path

    return make


def vulnerabilities_of(store, repo, snapshot_id, database_path):
    document = json.loads(
        export_sbom(store, repo, snapshot_id, packages=True, database=database_path)
    )
    return document.get("vulnerabilities", []), {
        p["name"]: p["value"] for p in document["metadata"]["properties"]
    }


def test_semver_precedence_matches_the_specification():
    order = [
        "0",
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-rc.1",
        "1.0.0",
        "1.0.1",
        "1.9.0",
        "1.10.0",
        "2.0.0",
    ]
    keys = [semver_key(value) for value in order]
    assert all(key is not None for key in keys)
    assert keys == sorted(keys)
    assert semver_key("1.0.0+build") == semver_key("1.0.0")
    assert semver_key("1.0") is None and semver_key("not-a-version") is None


def test_exact_version_list_matches(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20", "4.17.19"])])
    found, properties = vulnerabilities_of(store, repo, snapshot_id, path)
    assert [v["id"] for v in found] == ["GHSA-list"]
    assert found[0]["analysis"]["state"] == "in_triage"
    assert found[0]["affects"][0]["ref"] == "pkg:npm/lodash@4.17.20|pinned"
    assert found[0]["references"] == [{"id": "CVE-2020-0001", "source": {"name": "OSV"}}]
    assert properties["veriflow:osv_reachability_analysis"] == "none"


@pytest.mark.parametrize(
    "bounds,expected",
    [
        (("4.17.0", "4.17.21"), True),
        (("4.17.0", "4.17.20"), False),
        (("4.17.21", None), False),
        (("0", None), True),
    ],
)
def test_semver_range_bounds(store, snapshot, database, bounds, expected):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    introduced, fixed = bounds
    path = database([osv("GHSA-range", "npm", "lodash", **semver_range(introduced, fixed))])
    found, _ = vulnerabilities_of(store, repo, snapshot_id, path)
    assert bool(found) is expected
    if expected:
        assert found[0]["properties"][0]["value"] == "semver_range"


def test_last_affected_is_inclusive(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database(
        [osv("GHSA-last", "npm", "lodash", **semver_range("4.0.0", last_affected="4.17.20"))]
    )
    found, _ = vulnerabilities_of(store, repo, snapshot_id, path)
    assert [v["id"] for v in found] == ["GHSA-last"]


def test_unevaluable_range_is_a_gap_not_a_clean_result(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    record = osv("GHSA-eco", "npm", "lodash")
    record["affected"][0]["ranges"] = [
        {"type": "ECOSYSTEM", "events": [{"introduced": "4.0.0"}, {"fixed": "4.17.21"}]}
    ]
    found, properties = vulnerabilities_of(store, repo, snapshot_id, database([record]))
    assert found == []
    # The component must not be counted as cleanly evaluated.
    assert "partially_evaluated=1" in properties["veriflow:osv_component_states"]
    assert "range_type_ECOSYSTEM_npm=1" in properties["veriflow:osv_evaluation_gaps"]


def test_semver_range_over_a_maven_qualifier_is_a_gap(store, snapshot, database):
    # A SEMVER-typed range demands semantic-version ordering, which a qualifier has not.
    repo, snapshot_id = snapshot({"pom.xml": POM.replace("5.3.9", "5.3.9.RELEASE")})
    path = database(
        [
            osv(
                "GHSA-maven",
                "Maven",
                "org.springframework:spring-web",
                **semver_range("5.0.0", "5.4.0"),
            )
        ]
    )
    found, properties = vulnerabilities_of(store, repo, snapshot_id, path)
    assert found == []
    assert "version_not_semver=1" in properties["veriflow:osv_evaluation_gaps"]
    assert "partially_evaluated=1" in properties["veriflow:osv_component_states"]


def ecosystem_range(introduced, fixed=None, last_affected=None):
    events = [{"introduced": introduced}]
    if fixed:
        events.append({"fixed": fixed})
    if last_affected:
        events.append({"last_affected": last_affected})
    return {"ranges": [{"type": "ECOSYSTEM", "events": events}]}


@pytest.mark.parametrize(
    "version,bounds,expected",
    [
        ("5.3.9", ("5.0.0", "5.4.0"), True),
        ("5.3.9", ("5.0.0", "5.3.9"), False),
        ("5.3.9.RELEASE", ("5.0.0", "5.4.0"), True),
        # Numeric, not lexical: a string compare would place 5.3.10 below 5.3.9 and match.
        ("5.3.10", ("5.0.0", "5.3.9"), False),
        ("5.3.10", ("5.0.0", "5.3.11"), True),
        ("1.0-SNAPSHOT", ("0", "1.0"), True),
        ("2.0", ("0", "1.0"), False),
    ],
)
def test_maven_ecosystem_ranges_are_evaluated(store, snapshot, database, version, bounds, expected):
    repo, snapshot_id = snapshot({"pom.xml": POM.replace("5.3.9", version)})
    introduced, fixed = bounds
    path = database(
        [
            osv(
                "GHSA-eco-mvn",
                "Maven",
                "org.springframework:spring-web",
                **ecosystem_range(introduced, fixed),
            )
        ]
    )
    found, properties = vulnerabilities_of(store, repo, snapshot_id, path)
    assert bool(found) is expected
    if expected:
        assert found[0]["properties"][0]["value"] == "maven_range"
    else:
        # Fully evaluated now, not a gap.
        assert "evaluated_no_match=1" in properties["veriflow:osv_component_states"]
        assert properties["veriflow:osv_evaluation_gaps"] == ""


def test_maven_ordering_is_not_applied_to_npm(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    record = osv("GHSA-eco-npm", "npm", "lodash", **ecosystem_range("4.0.0", "4.17.21"))
    found, properties = vulnerabilities_of(store, repo, snapshot_id, database([record]))
    assert found == []
    assert "range_type_ECOSYSTEM_npm=1" in properties["veriflow:osv_evaluation_gaps"]


def test_semver_typed_range_is_evaluated_for_any_ecosystem(store, snapshot, database):
    # The record itself declares SEMVER ordering, and this version satisfies it.
    repo, snapshot_id = snapshot({"pom.xml": POM})
    path = database(
        [
            osv(
                "GHSA-mvn-semver",
                "Maven",
                "org.springframework:spring-web",
                **semver_range("5.0.0", "5.4.0"),
            )
        ]
    )
    found, _ = vulnerabilities_of(store, repo, snapshot_id, path)
    assert [v["id"] for v in found] == ["GHSA-mvn-semver"]
    assert found[0]["properties"][0]["value"] == "semver_range"


def test_maven_version_list_matches_on_group_and_artifact(store, snapshot, database):
    repo, snapshot_id = snapshot({"pom.xml": POM})
    path = database(
        [osv("GHSA-mvn", "Maven", "org.springframework:spring-web", versions=["5.3.9"])]
    )
    found, _ = vulnerabilities_of(store, repo, snapshot_id, path)
    assert [v["id"] for v in found] == ["GHSA-mvn"]
    reference = "pkg:maven/org.springframework/spring-web@5.3.9|declared_version"
    assert found[0]["affects"][0]["ref"] == reference


def test_withdrawn_record_never_matches(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    record = osv("GHSA-gone", "npm", "lodash", versions=["4.17.20"])
    record["withdrawn"] = "2026-01-01T00:00:00Z"
    found, properties = vulnerabilities_of(store, repo, snapshot_id, database([record]))
    assert found == []
    assert properties["veriflow:osv_records_loaded"] == "0"


def test_unresolved_version_is_never_evaluated(store, snapshot, database):
    repo, snapshot_id = snapshot({"package.json": {"dependencies": {"lodash": "^4.17.0"}}})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    found, properties = vulnerabilities_of(store, repo, snapshot_id, path)
    assert found == []
    assert "not_evaluated=1" in properties["veriflow:osv_component_states"]
    assert "component_state_no_version=1" in properties["veriflow:osv_evaluation_gaps"]


def test_npm_name_case_is_normalized(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-case", "npm", "LoDash", versions=["4.17.20"])])
    found, _ = vulnerabilities_of(store, repo, snapshot_id, path)
    assert [v["id"] for v in found] == ["GHSA-case"]


def test_unmatched_component_is_reported_as_evaluated(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-other", "npm", "lodash", versions=["3.0.0"])])
    _, properties = vulnerabilities_of(store, repo, snapshot_id, path)
    assert "evaluated_no_match=2" in properties["veriflow:osv_component_states"]
    assert properties["veriflow:osv_evaluation_gaps"] == ""


def test_matching_requires_packages(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    with pytest.raises(VeriFlowError, match="requires --packages"):
        export_sbom(store, repo, snapshot_id, database=path)


def test_database_integrity_is_enforced(store, snapshot, database, tmp_path):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    (tmp_path / "osv" / "records" / "GHSA-list.json").write_text('{"id": "GHSA-tampered"}')
    with pytest.raises(VeriFlowError, match="integrity mismatch"):
        export_sbom(store, repo, snapshot_id, packages=True, database=path)


def test_added_record_breaks_the_pinned_inventory(store, snapshot, database, tmp_path):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    (tmp_path / "osv" / "records" / "extra.json").write_text('{"id": "GHSA-extra"}')
    with pytest.raises(VeriFlowError, match="record count"):
        export_sbom(store, repo, snapshot_id, packages=True, database=path)


@pytest.mark.parametrize(
    "override",
    [{"version": "2"}, {"ecosystems": ["PyPI"]}, {"records_directory": "../escape"}],
)
def test_invalid_profile_is_refused(store, snapshot, database, override):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])], **override)
    with pytest.raises(VeriFlowError, match="Invalid OSV database profile"):
        export_sbom(store, repo, snapshot_id, packages=True, database=path)


def test_osv_export_groups_by_declaring_file(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    document = json.loads(export_osv(store, repo, snapshot_id, path))
    assert [result["source"] for result in document["results"]] == [
        {"path": "package-lock.json", "type": "lockfile"}
    ]
    package = document["results"][0]["packages"][0]
    assert package["package"] == {
        "name": "lodash",
        "version": "4.17.20",
        "ecosystem": "npm",
        "purl": "pkg:npm/lodash@4.17.20",
    }
    assert package["vulnerabilities"][0]["id"] == "GHSA-list"
    assert package["veriflow"]["match_bases"] == ["version_list"]
    assert document["veriflow"]["snapshot_id"] == snapshot_id


def test_empty_osv_result_states_its_limits(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([])
    document = json.loads(export_osv(store, repo, snapshot_id, path))
    assert document["results"] == []
    assert any("never means" in line for line in document["veriflow"]["limitations"])
    assert document["veriflow"]["osv_coverage"]["reachability_analysis"] == "none"
    assert document["veriflow"]["dependency_coverage"]["transitive_resolved"] is False


def test_osv_matching_is_deterministic_and_exposed_on_the_cli(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    first = export_osv(store, repo, snapshot_id, path)
    assert first == export_osv(store, repo, snapshot_id, path)
    result = CliRunner().invoke(
        app, ["--state-dir", str(store.root), "get-osv", repo, snapshot_id, str(path)]
    )
    assert result.exit_code == 0 and result.stdout_bytes == first


def test_usage_evidence_never_changes_the_analysis_state(store, snapshot, database):
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    cases = (('require("lodash");', "import_observed"), ("var x = 1;", "not_observed"))
    for source, expected in cases:
        repo, snapshot_id = snapshot({"package-lock.json": LOCK, "src/app.js": source})
        document = json.loads(
            export_sbom(store, repo, snapshot_id, packages=True, database=path, usage=True)
        )
        found = document["vulnerabilities"]
        assert [v["id"] for v in found] == ["GHSA-list"]
        # Usage prioritizes; it never adjudicates.
        assert found[0]["analysis"]["state"] == "in_triage"
        properties = {p["name"]: p["value"] for p in found[0]["properties"]}
        assert properties["veriflow:usage_state"] == expected


def test_osv_export_carries_usage_and_states_its_limits(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK, "src/app.js": "var x = 1;"})
    path = database([osv("GHSA-list", "npm", "lodash", versions=["4.17.20"])])
    document = json.loads(export_osv(store, repo, snapshot_id, path, usage=True))
    package = document["results"][0]["packages"][0]
    assert package["veriflow"]["usage"]["state"] == "not_observed"
    coverage = document["veriflow"]["usage_coverage"]
    assert coverage["analysis"] == "import evidence only; not reachability"
    assert coverage["call_graph_resolved"] is False
    assert coverage["vulnerable_symbol_matching"] == "none"
    assert coverage["third_party_source_available"] is False
    assert any("never clears" in line for line in document["veriflow"]["limitations"])


GOMOD = "module github.com/example/app\nrequire github.com/gin-gonic/gin v1.9.1\n"


def test_go_module_is_keyed_on_its_full_path(store, snapshot, database):
    repo, snapshot_id = snapshot({"go.mod": GOMOD})
    path = database([osv("GHSA-go", "Go", "github.com/gin-gonic/gin", versions=["v1.9.1"])])
    found, _ = vulnerabilities_of(store, repo, snapshot_id, path)
    assert [v["id"] for v in found] == ["GHSA-go"]
    assert found[0]["affects"][0]["ref"] == (
        "pkg:golang/github.com/gin-gonic/gin@v1.9.1|declared_version"
    )


def test_go_version_list_matches_without_the_v_prefix(store, snapshot, database):
    # OSV Go records write plain semantic versions; go.mod carries the v prefix.
    repo, snapshot_id = snapshot({"go.mod": GOMOD})
    path = database([osv("GHSA-go-plain", "Go", "github.com/gin-gonic/gin", versions=["1.9.1"])])
    found, _ = vulnerabilities_of(store, repo, snapshot_id, path)
    assert [v["id"] for v in found] == ["GHSA-go-plain"]


@pytest.mark.parametrize(
    "bounds,expected",
    [(("1.9.0", "1.9.2"), True), (("1.9.0", "1.9.1"), False), (("1.9.2", None), False)],
)
def test_go_semver_ranges_use_the_stripped_version(store, snapshot, database, bounds, expected):
    repo, snapshot_id = snapshot({"go.mod": GOMOD})
    introduced, fixed = bounds
    path = database(
        [osv("GHSA-go-range", "Go", "github.com/gin-gonic/gin", **semver_range(introduced, fixed))]
    )
    found, properties = vulnerabilities_of(store, repo, snapshot_id, path)
    assert bool(found) is expected
    if not expected:
        assert "evaluated_no_match=1" in properties["veriflow:osv_component_states"]
        assert properties["veriflow:osv_evaluation_gaps"] == ""


def test_replaced_module_is_never_matched(store, snapshot, database):
    source = GOMOD + "replace github.com/gin-gonic/gin => github.com/fork/gin v1.9.9\n"
    repo, snapshot_id = snapshot({"go.mod": source})
    path = database([osv("GHSA-go", "Go", "github.com/gin-gonic/gin", versions=["v1.9.1"])])
    found, properties = vulnerabilities_of(store, repo, snapshot_id, path)
    # The declared version is not what a build resolves, so it is never evaluated.
    assert found == []
    assert "component_state_no_version=1" in properties["veriflow:osv_evaluation_gaps"]
