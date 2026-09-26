import json

import pytest
from test_dependency_discovery import snapshot as snapshot
from test_osv_matching import LOCK, osv
from test_osv_matching import database as database

from veriflow.domain import VeriFlowError
from veriflow.osv_database import cache_path, prepare, read_profile
from veriflow.sbom_export import export_sbom

RECORD = osv("GHSA-cache", "npm", "lodash", versions=["4.17.20"])


def verifications(document):
    """Pull the verification marker from either document shape."""
    properties = document.get("metadata", {}).get("properties", [])
    found = [p["value"] for p in properties if p["name"] == "veriflow:osv_database_verification"]
    coverage = document.get("veriflow", {}).get("osv_coverage", {})
    return found or [coverage["database_verification"]]


def scrubbed(document):
    return json.loads(
        json.dumps(document).replace('"reverified"', '"X"').replace('"cached"', '"X"')
    )


def verification_of(store, repo, snapshot_id, path, **options):
    document = json.loads(
        export_sbom(store, repo, snapshot_id, packages=True, database=path, **options)
    )
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    return properties["veriflow:osv_database_verification"], document.get("vulnerabilities", [])


def test_cache_is_opt_in(store, database, tmp_path):
    path = database([RECORD])
    prepared = prepare(path)
    assert prepared["verification"] == "reverified"
    assert not (store.root / "osv-cache").exists()


def test_cache_hit_reproduces_the_rebuilt_index(store, database):
    path = database([RECORD, osv("GHSA-two", "Maven", "org.example:lib", versions=["1.0"])])
    fresh = prepare(path)
    first = prepare(path, store.root)
    assert first["verification"] == "reverified"
    assert cache_path(store.root, read_profile(path)).is_file()
    warm = prepare(path, store.root)
    assert warm["verification"] == "cached"
    assert set(warm["index"]) == set(fresh["index"])
    for key in fresh["index"]:
        assert [r["id"] for r, _ in warm["index"][key]] == [r["id"] for r, _ in fresh["index"][key]]
    assert warm["loading"] == fresh["loading"]


def test_cached_matching_produces_the_same_candidates(store, snapshot, database):
    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([RECORD])
    cold, first = verification_of(store, repo, snapshot_id, path, cache=True)
    warm, second = verification_of(store, repo, snapshot_id, path, cache=True)
    assert cold == "reverified" and warm == "cached"
    assert [v["id"] for v in first] == [v["id"] for v in second] == ["GHSA-cache"]
    assert first[0]["analysis"]["state"] == second[0]["analysis"]["state"] == "in_triage"


def test_a_changed_database_invalidates_the_cache(store, database, tmp_path):
    path = database([RECORD])
    prepare(path, store.root)
    # A new profile pins a different inventory digest, so the old cache cannot apply.
    other = database([RECORD, osv("GHSA-extra", "npm", "left-pad", versions=["1.3.0"])])
    prepared = prepare(other, store.root)
    assert prepared["verification"] == "reverified"
    assert ("npm", "left-pad") in prepared["index"]


def test_cache_naming_a_different_inventory_is_rejected(store, database):
    path = database([RECORD])
    prepare(path, store.root)
    saved = cache_path(store.root, read_profile(path))
    payload = json.loads(saved.read_text())
    payload["inventory_sha256"] = "0" * 64
    saved.write_text(json.dumps(payload))
    assert prepare(path, store.root)["verification"] == "reverified"


@pytest.mark.parametrize("content", ["not json", '{"schema_version": "2"}', "{}", "[]"])
def test_unusable_cache_falls_back_to_a_verified_rebuild(store, database, content):
    path = database([RECORD])
    prepare(path, store.root)
    cache_path(store.root, read_profile(path)).write_text(content)
    prepared = prepare(path, store.root)
    assert prepared["verification"] == "reverified"
    assert ("npm", "lodash") in prepared["index"]


def test_refresh_rebuilds_and_overwrites(store, database):
    path = database([RECORD])
    prepare(path, store.root)
    saved = cache_path(store.root, read_profile(path))
    saved.write_text(json.dumps({"schema_version": "1", "inventory_sha256": "x"}))
    prepared = prepare(path, store.root, refresh=True)
    assert prepared["verification"] == "reverified"
    assert json.loads(saved.read_text())["schema_version"] == "1"
    assert prepare(path, store.root)["verification"] == "cached"


def test_symlinked_cache_is_refused(store, database, tmp_path):
    path = database([RECORD])
    prepare(path, store.root)
    saved = cache_path(store.root, read_profile(path))
    target = tmp_path / "elsewhere.json"
    target.write_text(saved.read_text())
    saved.unlink()
    saved.symlink_to(target)
    assert prepare(path, store.root)["verification"] == "reverified"


def test_unwritable_cache_never_fails_the_scan(store, database, monkeypatch):
    path = database([RECORD])

    def refuse(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr("pathlib.Path.mkdir", refuse)
    prepared = prepare(path, store.root)
    assert prepared["verification"] == "reverified"
    assert ("npm", "lodash") in prepared["index"]


def test_a_tampered_record_is_caught_without_the_cache(store, database, tmp_path):
    path = database([RECORD])
    (tmp_path / "osv" / "records" / "GHSA-cache.json").write_text('{"id": "GHSA-tampered"}')
    with pytest.raises(VeriFlowError, match="integrity mismatch"):
        prepare(path)


def test_the_cache_trades_record_verification_for_speed(store, database, tmp_path):
    """A cache hit does not re-read the records, so later tampering is not detected."""
    path = database([RECORD])
    assert prepare(path, store.root)["verification"] == "reverified"
    (tmp_path / "osv" / "records" / "GHSA-cache.json").write_text('{"id": "GHSA-tampered"}')
    # Without the cache the same database is refused outright.
    with pytest.raises(VeriFlowError, match="integrity mismatch"):
        prepare(path)
    # With it, the approved contents are served and the change goes unnoticed.
    prepared = prepare(path, store.root)
    assert prepared["verification"] == "cached"
    assert [r["id"] for r, _ in prepared["index"][("npm", "lodash")]] == ["GHSA-cache"]
    # Refreshing restores full verification and refuses.
    with pytest.raises(VeriFlowError, match="integrity mismatch"):
        prepare(path, store.root, refresh=True)


def test_cache_options_reach_both_commands(store, snapshot, database):
    """The CLI wiring is exercised here; calling export_sbom directly would not catch it."""
    from typer.testing import CliRunner

    from veriflow.cli import app

    repo, snapshot_id = snapshot({"package-lock.json": LOCK})
    path = database([RECORD])
    base = ["--state-dir", str(store.root)]
    runner = CliRunner()
    seen = []
    for command in (
        [*base, "get-sbom", repo, snapshot_id, "--packages", "--database", str(path), "--cache"],
        [*base, "get-osv", repo, snapshot_id, str(path), "--cache"],
    ):
        first = runner.invoke(app, command)
        assert first.exit_code == 0, first.output
        second = runner.invoke(app, command)
        assert second.exit_code == 0, second.output
        # The only difference a cache may make is the verification it reports.
        cold, warm = json.loads(first.stdout), json.loads(second.stdout)
        assert scrubbed(cold) == scrubbed(warm)
        seen += verifications(cold) + verifications(warm)
    # One verified build, then reuse -- including across commands, since the cache is
    # keyed by the profile digest rather than by the command that wrote it.
    assert seen == ["reverified", "cached", "cached", "cached"]
    assert list((store.root / "osv-cache").glob("*.json"))
    refreshed = runner.invoke(
        app, [*base, "get-osv", repo, snapshot_id, str(path), "--cache", "--refresh-cache"]
    )
    assert refreshed.exit_code == 0, refreshed.output
    assert verifications(json.loads(refreshed.stdout)) == ["reverified"]


def test_every_declared_cli_option_is_accepted(store):
    """Guards against an option that exists in the function but never reaches the command."""
    from typer.testing import CliRunner

    from veriflow.cli import app

    for command, expected in (
        (
            "get-sbom",
            {"--verify", "--packages", "--database", "--usage", "--cache", "--refresh-cache"},
        ),
        ("get-osv", {"--verify", "--usage", "--cache", "--refresh-cache"}),
    ):
        output = CliRunner().invoke(app, [command, "--help"]).output
        missing = {option for option in expected if option not in output}
        assert not missing, f"{command} is missing {sorted(missing)}"
