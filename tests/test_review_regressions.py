"""One test per defect found reviewing 9063d54^..HEAD; each fails against the original code."""

import json

import pytest
from test_dependency_discovery import properties_of
from test_dependency_discovery import snapshot as snapshot
from test_osv_matching import LOCK, osv
from test_osv_matching import database as database

from veriflow.domain import TraceProofError
from veriflow.go_modules import parse as parse_gomod
from veriflow.maven_poms import parse as parse_pom
from veriflow.maven_version import maven_key
from veriflow.osv_export import export_osv
from veriflow.osv_matching import semver_key
from veriflow.sbom_export import export_sbom

NS = 'xmlns="http://maven.apache.org/POM/4.0.0"'


def coverage_of(store, repo, snapshot_id, **options):
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, **options))
    return {p["name"]: p["value"] for p in document["metadata"]["properties"]}, document


def test_component_outside_the_database_ecosystems_is_not_evaluated(store, snapshot, database):
    """An npm component against a Maven-only export was reported as cleanly evaluated."""
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-mvn", "Maven", "g:a", versions=["1.0"])], ecosystems=["Maven"])
    properties, _ = coverage_of(store, repo, snapshot_id, database=path)
    assert "evaluated_no_match" not in properties["veriflow:osv_component_states"]
    assert "not_evaluated=2" in properties["veriflow:osv_component_states"]
    assert (
        "component_state_ecosystem_not_in_database=2"
        in (properties["veriflow:osv_evaluation_gaps"])
    )


def test_unreadable_records_prevent_a_clean_classification(store, snapshot, database):
    """A record the loader could not parse is unread evidence, not absent evidence."""
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database(
        [osv("GHSA-other", "npm", "left-pad", versions=["9.9.9"])],
        raw_files={"broken.json": b"{not json"},
    )
    properties, _ = coverage_of(store, repo, snapshot_id, database=path)
    assert "evaluated_no_match" not in properties["veriflow:osv_component_states"]
    assert "partially_evaluated" in properties["veriflow:osv_component_states"]
    assert "component_state_database_incomplete=2" in (properties["veriflow:osv_evaluation_gaps"])


def test_withdrawn_records_alone_still_allow_a_clean_classification(store, snapshot, database):
    """A withdrawn advisory is deliberately excluded, not unread."""
    withdrawn = {
        **osv("GHSA-gone", "npm", "lodash", versions=["4.17.20"]),
        "withdrawn": "2026-01-01",
    }
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([withdrawn, osv("GHSA-other", "npm", "left-pad", versions=["9.9.9"])])
    properties, document = coverage_of(store, repo, snapshot_id, database=path)
    assert not document.get("vulnerabilities")
    assert "evaluated_no_match=2" in properties["veriflow:osv_component_states"]
    assert properties["veriflow:osv_evaluation_gaps"] == ""


def test_excess_matches_refuse_rather_than_truncate(store, snapshot, database, monkeypatch):
    """Silently dropping candidates would publish a partial security result."""
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database(
        [osv(f"GHSA-{index:04d}", "npm", "lodash", versions=["4.17.20"]) for index in range(4)]
    )
    monkeypatch.setattr("veriflow.osv_matching.MAX_MATCHES", 2)
    with pytest.raises(TraceProofError, match="result limit"):
        export_sbom(store, repo, snapshot_id, packages=True, database=path)


def test_managed_range_is_not_reported_as_a_version():
    """A dependencyManagement entry may itself carry a range."""
    body = (
        f"<project {NS}><groupId>com.example</groupId><artifactId>app</artifactId>"
        "<dependencyManagement><dependencies><dependency>"
        "<groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId>"
        "<version>[1,2)</version></dependency></dependencies></dependencyManagement>"
        "<dependencies><dependency>"
        "<groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId>"
        "</dependency></dependencies></project>"
    )
    records, reason, _ = parse_pom(body.encode(), "pom.xml")
    assert reason is None and len(records) == 1
    assert records[0]["version"] is None
    assert records[0]["resolution"] == "declared_range"
    assert records[0]["constraint"] == "[1,2)"
    assert "@" not in records[0]["purl"]


def test_inapplicable_replacement_emits_no_phantom_component():
    """A replacement naming a version this module does not require applies to nothing."""
    source = (
        b"module github.com/example/app\n"
        b"require github.com/c/d v3.0.0\n"
        b"replace github.com/c/d v9.9.9 => github.com/c/d v9.9.10\n"
    )
    records, reason, notes = parse_gomod(source, "go.mod")
    assert reason is None
    assert [r["purl"] for r in records] == ["pkg:golang/github.com/c/d@v3.0.0"]
    assert not notes.get("replaced_requirements")


def test_applicable_replacement_still_emits_its_target():
    source = (
        b"module github.com/example/app\n"
        b"require github.com/c/d v3.0.0\n"
        b"replace github.com/c/d v3.0.0 => github.com/e/f v4.0.0\n"
    )
    records, _, notes = parse_gomod(source, "go.mod")
    purls = {r["purl"] for r in records}
    assert purls == {"pkg:golang/github.com/c/d", "pkg:golang/github.com/e/f@v4.0.0"}
    assert notes["replaced_requirements"] == 1


@pytest.mark.parametrize(
    "parser,source,limit,match",
    [
        (
            parse_gomod,
            b"module x\n"
            + b"".join(f"require example.com/m{i} v1.0.0\n".encode() for i in range(6)),
            "veriflow.go_modules.MAX_REQUIREMENTS",
            "requirement limit",
        ),
        (
            parse_pom,
            (
                f"<project {NS}><groupId>g</groupId><artifactId>a</artifactId><dependencies>"
                + "".join(
                    f"<dependency><groupId>g{i}</groupId><artifactId>a{i}</artifactId>"
                    f"<version>1.0</version></dependency>"
                    for i in range(6)
                )
                + "</dependencies></project>"
            ).encode(),
            "veriflow.maven_poms.MAX_DEPENDENCIES",
            "dependency limit",
        ),
    ],
)
def test_declaration_limits_refuse_rather_than_truncate(parser, source, limit, match, monkeypatch):
    monkeypatch.setattr(limit, 2)
    with pytest.raises(TraceProofError, match=match):
        parser(source, "manifest")


@pytest.mark.parametrize("key", [semver_key, maven_key])
def test_absurd_version_segments_do_not_crash_ordering(key):
    """An untrusted manifest must not reach Python's integer conversion limit."""
    assert key("1.0." + "9" * 5000) is None
    assert key("1." + "9" * 5000) is None


def test_go_rejects_an_unbounded_version():
    source = b"module x\nrequire example.com/m v1.0." + b"9" * 5000 + b"\n"
    records, reason, _ = parse_gomod(source, "go.mod")
    assert reason is None and records == []


def test_osv_output_limit_is_enforced(store, snapshot, database, monkeypatch):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-big", "npm", "lodash", versions=["4.17.20"])])
    monkeypatch.setattr("veriflow.osv_export.MAX_OSV_BYTES", 10)
    with pytest.raises(TraceProofError, match="8 MiB"):
        export_osv(store, repo, snapshot_id, path)


def test_metadata_does_not_deny_analysis_the_document_carries(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-x", "npm", "lodash", versions=["4.17.20"])])
    without, _ = coverage_of(store, repo, snapshot_id)
    assert without["veriflow:vulnerability_analysis"] == "not_included"
    with_db, document = coverage_of(store, repo, snapshot_id, database=path)
    assert document["vulnerabilities"]
    assert with_db["veriflow:vulnerability_analysis"] == "osv_version_range_matching"


def test_a_matched_component_still_reports_its_ecosystem_covered(store, snapshot, database):
    """The coverage fix must not suppress ordinary matching."""
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-x", "npm", "lodash", versions=["4.17.20"])])
    properties, document = coverage_of(store, repo, snapshot_id, database=path)
    assert [v["id"] for v in document["vulnerabilities"]] == ["GHSA-x"]
    assert "matched=1" in properties["veriflow:osv_component_states"]
    assert properties["veriflow:osv_evaluation_gaps"] == ""
    libs = [c for c in document["components"] if c["type"] == "library"]
    assert any(properties_of(c)["veriflow:resolution"] == "pinned" for c in libs)


# --- Second review pass ---------------------------------------------------------------


@pytest.mark.parametrize(
    "affected",
    [
        {"package": {"ecosystem": "npm", "name": "lodash"}},
        [{"package": {"ecosystem": "npm", "name": "lodash"}, "versions": [{}]}],
        [{"package": {"ecosystem": "npm", "name": "lodash"}, "ranges": "oops"}],
        [{"package": {"ecosystem": "npm", "name": "lodash"}, "ranges": [{"events": "oops"}]}],
        [{"package": {"ecosystem": "npm", "name": 7}}],
        ["not-an-entry"],
    ],
)
def test_malformed_nested_records_are_unread_not_empty(store, snapshot, database, affected):
    """Nested shape was unvalidated: some shapes read clean, others raised TypeError."""
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([{"id": "GHSA-bad", "aliases": [], "affected": affected}])
    properties, document = coverage_of(store, repo, snapshot_id, database=path)
    assert not document.get("vulnerabilities")
    assert "evaluated_no_match" not in properties["veriflow:osv_component_states"]
    assert "partially_evaluated" in properties["veriflow:osv_component_states"]
    assert properties["veriflow:osv_records_unread"] == "1"


def test_matched_components_are_not_fully_evaluated_against_an_incomplete_database(
    store, snapshot, database
):
    """A match against a database with unread records is still not a complete evaluation."""
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database(
        [osv("GHSA-hit", "npm", "lodash", versions=["4.17.20"])],
        raw_files={"broken.json": b"{not json"},
    )
    properties, document = coverage_of(store, repo, snapshot_id, database=path)
    assert [v["id"] for v in document["vulnerabilities"]] == ["GHSA-hit"]
    # The matched state stays; the accounting and coverage must disclose the gap.
    assert "matched=1" in properties["veriflow:osv_component_states"]
    assert properties["veriflow:osv_components_fully_evaluated"] == "0"
    assert properties["veriflow:osv_records_unread"] == "1"
    assert "component_state_database_incomplete=2" in (properties["veriflow:osv_evaluation_gaps"])


def test_match_accumulation_stops_at_the_limit(store, snapshot, database, monkeypatch):
    """The limit was applied after one component had already materialized every match."""
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv(f"GHSA-{i:03d}", "npm", "lodash", versions=["4.17.20"]) for i in range(8)])
    monkeypatch.setattr("veriflow.osv_matching.MAX_MATCHES", 3)
    built = []
    original = __import__("veriflow.osv_matching", fromlist=["match_record"]).match_record

    def counting(*args, **kwargs):
        built.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr("veriflow.osv_matching.match_record", counting)
    with pytest.raises(TraceProofError, match="result limit"):
        export_sbom(store, repo, snapshot_id, packages=True, database=path)
    # Refused as the limit was crossed, not after building all eight.
    assert len(built) == 4


def test_oversized_advisory_prose_is_bounded(store, snapshot, database):
    """An unbounded upstream summary must not size the output."""
    from veriflow.osv_matching import MAX_SUMMARY_CHARS

    record = osv("GHSA-long", "npm", "lodash", versions=["4.17.20"])
    record["summary"] = "x" * (MAX_SUMMARY_CHARS * 3)
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([record])
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, database=path))
    carried = document["vulnerabilities"][0]["description"]
    assert len(carried) == MAX_SUMMARY_CHARS
    osv_document = json.loads(export_osv(store, repo, snapshot_id, path))
    entry = osv_document["results"][0]["packages"][0]["vulnerabilities"][0]
    assert entry["veriflow_summary_truncated"] is True


def test_osv_output_limit_applies_while_encoding(store, snapshot, database, monkeypatch):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([osv("GHSA-x", "npm", "lodash", versions=["4.17.20"])])
    monkeypatch.setattr("veriflow.osv_export.MAX_OSV_BYTES", 50)
    with pytest.raises(TraceProofError, match="8 MiB"):
        export_osv(store, repo, snapshot_id, path)


def test_valid_records_are_still_accepted(store, snapshot, database):
    """The nested validation must not reject well-formed advisories."""
    record = osv("GHSA-ok", "npm", "lodash", versions=["4.17.20"])
    record["affected"][0]["ranges"] = [
        {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "5.0.0"}]}
    ]
    record["affected"][0]["ecosystem_specific"] = {"imports": [{"path": "p", "symbols": ["S"]}]}
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    properties, document = coverage_of(store, repo, snapshot_id, database=database([record]))
    assert [v["id"] for v in document["vulnerabilities"]] == ["GHSA-ok"]
    assert properties["veriflow:osv_records_unread"] == "0"
    assert "matched=1" in properties["veriflow:osv_component_states"]
