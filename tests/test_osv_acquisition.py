import hashlib
import io
import json
import zipfile

import pytest

from veriflow.domain import TraceProofError
from veriflow.osv_acquisition import acquire_osv
from veriflow.osv_database import build_index, load_profile

HOSTS = ["osv-vulnerabilities.storage.googleapis.com"]
SOURCE = "https://osv-vulnerabilities.storage.googleapis.com"


def record(identifier, ecosystem="npm", name="lodash"):
    return {
        "id": identifier,
        "affected": [{"package": {"ecosystem": ecosystem, "name": name}, "versions": ["4.17.20"]}],
    }


def archive(records, **members):
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as out:
        for item in records:
            out.writestr(f"{item['id']}.json", json.dumps(item))
        for name, body in members.items():
            out.writestr(name, body)
    return raw.getvalue()


class FakeReader:
    def __init__(self, archives):
        self.archives = archives
        self.urls = []

    def fetch(self, url, max_bytes):
        self.urls.append(url)
        ecosystem = url.rsplit("/", 2)[-2]
        if ecosystem not in self.archives:
            raise TraceProofError("OSV archive fetch failed (HTTPError)")
        return self.archives[ecosystem]


@pytest.fixture
def acquire(tmp_path):
    def run(archives, output="export", **overrides):
        options = {
            "base_url": SOURCE,
            "ecosystems": sorted(archives),
            "allowed_hosts": HOSTS,
            "output": tmp_path / output,
            "allow_unpinned": True,
            **overrides,
        }
        reader = FakeReader(archives)
        return reader, acquire_osv(reader, **options)

    return run


def test_acquisition_writes_a_profile_the_matcher_accepts(acquire, tmp_path):
    reader, result = acquire({"npm": archive([record("GHSA-a"), record("GHSA-b")])})
    assert reader.urls == [f"{SOURCE}/npm/all.zip"]
    assert result["record_count"] == 2 and result["state"] == "acquired"
    profile = load_profile(result["profile"])
    assert profile["ecosystems"] == ["npm"] and profile["source"] == SOURCE
    index, loading = build_index(profile)
    assert loading["records_loaded"] == 2
    assert index[("npm", "lodash")]


def test_records_are_read_only_and_profile_is_pinned(acquire, tmp_path):
    _, result = acquire({"npm": archive([record("GHSA-a")])})
    written = tmp_path / "export" / "records" / "GHSA-a.json"
    assert written.stat().st_mode & 0o777 == 0o400
    written.chmod(0o600)
    written.write_text('{"id": "GHSA-tampered"}')
    with pytest.raises(TraceProofError, match="integrity mismatch"):
        load_profile(result["profile"])


def test_several_ecosystems_are_fetched_and_recorded(acquire):
    reader, result = acquire(
        {
            "npm": archive([record("GHSA-a")]),
            "Maven": archive([record("GHSA-m", "Maven", "org.example:lib")]),
        }
    )
    assert reader.urls == [f"{SOURCE}/Maven/all.zip", f"{SOURCE}/npm/all.zip"]
    assert [entry["ecosystem"] for entry in result["archives"]] == ["Maven", "npm"]
    assert result["record_count"] == 2
    assert load_profile(result["profile"])["ecosystems"] == ["Maven", "npm"]


def test_shared_advisory_is_written_once(acquire):
    shared = record("GHSA-shared")
    _, result = acquire({"npm": archive([shared]), "Maven": archive([shared])})
    assert result["record_count"] == 1 and result["duplicate_records_skipped"] == 1
    index, loading = build_index(load_profile(result["profile"]))
    assert loading["records_loaded"] == 1


def test_disagreeing_archives_are_refused(acquire):
    first = record("GHSA-shared")
    second = {**record("GHSA-shared"), "summary": "different"}
    with pytest.raises(TraceProofError, match="disagree"):
        acquire({"npm": archive([first]), "Maven": archive([second])})


@pytest.mark.parametrize(
    "member",
    [
        {"nested/GHSA-x.json": "{}"},
        {"../escape.json": "{}"},
        {"notes.txt": "hello"},
        {".hidden.json": "{}"},
    ],
)
def test_unexpected_member_aborts_rather_than_skips(acquire, member):
    # A silently incomplete database would later read as a fully evaluated one.
    with pytest.raises(TraceProofError, match="flat JSON record"):
        acquire({"npm": archive([record("GHSA-a")], **member)})


def test_oversized_record_is_refused(acquire, monkeypatch):
    monkeypatch.setattr("veriflow.osv_acquisition.MAX_RECORD_BYTES", 10)
    with pytest.raises(TraceProofError, match="per-record byte limit"):
        acquire({"npm": archive([record("GHSA-a")])})


def test_record_limit_is_refused(acquire, monkeypatch):
    monkeypatch.setattr("veriflow.osv_acquisition.MAX_RECORDS", 1)
    with pytest.raises(TraceProofError, match="record limit"):
        acquire({"npm": archive([record("GHSA-a"), record("GHSA-b")])})


def test_expanded_byte_limit_is_refused(acquire, monkeypatch):
    monkeypatch.setattr("veriflow.osv_acquisition.MAX_EXPANDED_BYTES", 5)
    with pytest.raises(TraceProofError, match="expanded byte limit"):
        acquire({"npm": archive([record("GHSA-a")])})


def test_compression_ratio_is_refused(acquire, monkeypatch):
    monkeypatch.setattr("veriflow.osv_acquisition.MAX_COMPRESSION_RATIO", 1)
    with pytest.raises(TraceProofError, match="compression ratio"):
        acquire({"npm": archive([{**record("GHSA-a"), "summary": "x" * 20000}])})


def test_corrupt_archive_is_refused(acquire):
    with pytest.raises(TraceProofError, match="expansion failed"):
        acquire({"npm": b"not a zip file"})


def test_expected_digest_is_enforced(acquire, tmp_path):
    raw = archive([record("GHSA-a")])
    digest = hashlib.sha256(raw).hexdigest()
    _, result = acquire({"npm": raw}, expected_sha256={"npm": digest}, allow_unpinned=False)
    assert result["archives"][0]["pinning"] == "operator_pinned"
    assert result["archives"][0]["archive_sha256"] == digest
    with pytest.raises(TraceProofError, match="expected digest"):
        acquire({"npm": raw}, output="other", expected_sha256={"npm": "0" * 64})


def test_unpinned_acquisition_requires_an_opt_in(acquire):
    with pytest.raises(TraceProofError, match="explicit opt-in"):
        acquire({"npm": archive([record("GHSA-a")])}, allow_unpinned=False)


def test_unpinned_acquisition_is_labelled_and_stated(acquire):
    _, result = acquire({"npm": archive([record("GHSA-a")])})
    assert result["archives"][0]["pinning"] == "observed_only"
    assert any("operator-approved digest" in line for line in result["limitations"])
    assert any("absent, not empty" in line for line in result["limitations"])
    assert result["model_calls"] == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://osv-vulnerabilities.storage.googleapis.com",
        "https://evil.example.invalid",
        "https://user:pw@osv-vulnerabilities.storage.googleapis.com",
        "https://osv-vulnerabilities.storage.googleapis.com:8443",
        "https://osv-vulnerabilities.storage.googleapis.com/a/../b",
    ],
)
def test_source_must_be_credential_free_https_on_an_allowed_host(acquire, url):
    with pytest.raises(TraceProofError, match="allowed host"):
        acquire({"npm": archive([record("GHSA-a")])}, base_url=url)


def test_unsupported_ecosystem_is_refused(acquire, tmp_path):
    with pytest.raises(TraceProofError, match="ecosystems TraceProof can evaluate"):
        acquire_osv(
            FakeReader({}),
            base_url=SOURCE,
            ecosystems=["PyPI"],
            allowed_hosts=HOSTS,
            output=tmp_path / "pypi",
            allow_unpinned=True,
        )


def test_existing_output_directory_is_refused(acquire, tmp_path):
    (tmp_path / "export").mkdir()
    with pytest.raises(TraceProofError, match="must not already exist"):
        acquire({"npm": archive([record("GHSA-a")])})


def test_receipt_records_what_was_fetched(acquire, tmp_path):
    _, result = acquire({"npm": archive([record("GHSA-a")])})
    saved = json.loads((tmp_path / "export" / "osv-acquisition-receipt.json").read_text())
    assert saved["kind"] == "osv" and saved["state"] == "acquired"
    assert saved["inventory_sha256"] == load_profile(result["profile"])["inventory_sha256"]
    assert saved["archives"][0]["url"] == f"{SOURCE}/npm/all.zip"
    assert saved["record_count"] == 1
