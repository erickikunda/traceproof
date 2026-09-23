import json

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from veriflow.csharp_dependencies import environment, inventory, load_profile
from veriflow.domain import VeriFlowError


def profile(tmp_path):
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    (sdk / "dotnet").write_bytes(b"synthetic sdk")
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "System.Web.dll").write_bytes(b"synthetic reference")
    document = dict(
        version="1",
        sdk_version="test",
        codeql_version="2.27.0",
        sdk=dict(directory="sdk", files=inventory(sdk)),
        references=dict(directory="refs", files=inventory(refs)),
    )
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(document))
    return path


def test_pin_inventory_and_generated_local_feed(tmp_path):
    p = load_profile(profile(tmp_path))
    assert p["file_count"] == 2 and len(p["id"]) == 64
    attempt = tmp_path / "attempt"
    (attempt / "source").mkdir(parents=True)
    env = environment(p, attempt)
    assert env["DOTNET_ROOT"] == str(tmp_path / "sdk")
    assert env["CODEQL_EXTRACTOR_CSHARP_BUILDLESS_NUGET_FEEDS_FALLBACK"].startswith("file:")
    assert "<clear/>" in (attempt / "source/NuGet.Config").read_text()


@pytest.mark.parametrize("change", ["modified", "extra", "missing", "symlink"])
def test_tampered_dependency_inventory_rejected(tmp_path, change):
    path = profile(tmp_path)
    target = tmp_path / "refs/System.Web.dll"
    if change == "modified":
        target.write_bytes(b"modified")
    elif change == "extra":
        (tmp_path / "refs/Extra.dll").write_bytes(b"extra")
    elif change == "missing":
        target.unlink()
    else:
        target.unlink()
        target.symlink_to(tmp_path / "sdk/dotnet")
    with pytest.raises(VeriFlowError):
        load_profile(path)


def test_outside_profile_root_rejected(tmp_path):
    path = profile(tmp_path)
    data = json.loads(path.read_text())
    data["sdk"]["directory"] = "../outside"
    path.write_text(json.dumps(data))
    with pytest.raises(VeriFlowError):
        load_profile(path)


def test_changed_profile_does_not_reuse_old_attempt(store, scanned, tmp_path, monkeypatch):
    from veriflow import pipeline
    from veriflow.persistence import ScanAttempt

    path = profile(tmp_path)
    with store.transaction() as session:
        attempt = session.get(ScanAttempt, scanned[2])
        attempt.report = {
            **attempt.report,
            "language": "csharp",
            "language_scope": {
                "adapter_profile": "csharp-source-only-v1",
                "dependency_profile": {"id": "old"},
            },
        }
    query = tmp_path / "query.ql"
    query.write_text("// query")

    def preflight(*args):
        raise VeriFlowError("Reached extraction preflight")

    monkeypatch.setattr(pipeline, "verified_source", preflight)
    with pytest.raises(VeriFlowError, match="Reached extraction"):
        pipeline.scan_run(
            store,
            scanned[1],
            query,
            language="csharp",
            skip_existing=True,
            csharp_dependency_profile=path,
        )


def test_sdk_version_mismatch_stops_before_extraction(
    store, archive, manifest, tmp_path, monkeypatch
):
    import subprocess
    import zipfile

    from test_indexing import captured

    from veriflow.codeql import extract
    from veriflow.persistence import exclusive_worker

    path = profile(tmp_path)
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("C.cs", "class C {}")
    run = captured(store, archive, manifest)
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: "/trusted/codeql")
    monkeypatch.setattr(
        "veriflow.codeql.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=b"wrong-version\n"),
    )
    monkeypatch.setattr(
        "veriflow.codeql.subprocess.Popen", lambda *a, **k: pytest.fail("extraction launched")
    )
    with exclusive_worker(store.root):
        result = extract(
            store,
            run,
            language="csharp",
            allow_csharp_downloads=True,
            csharp_dependency_profile=path,
        )
    assert result["status"] == "dependency_toolchain_mismatch"


def test_isolation_failure_is_durable_and_launches_no_extractor(
    store, archive, manifest, tmp_path, monkeypatch
):
    import subprocess
    import zipfile

    from test_indexing import captured

    from veriflow.codeql import extract, extraction_status
    from veriflow.persistence import exclusive_worker

    path = profile(tmp_path)
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("C.cs", "class C {}")
    run = captured(store, archive, manifest)
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: "/trusted/codeql")
    monkeypatch.setattr("veriflow.codeql.offline_command", lambda _: ["/sandbox"])

    def denied(*args, **kwargs):
        raise subprocess.CalledProcessError(71, args[0])

    monkeypatch.setattr("veriflow.codeql.subprocess.run", denied)
    monkeypatch.setattr(
        "veriflow.codeql.subprocess.Popen", lambda *a, **k: pytest.fail("extraction launched")
    )
    with exclusive_worker(store.root):
        result = extract(
            store, run, language="csharp", csharp_dependency_profile=path, csharp_offline=True
        )
    assert result["status"] == "network_isolation_unavailable"
    assert not result["language_scope"]["dependency_profile"]["network_denial_verified"]
    assert extraction_status(store, result["attempt_id"])["status"] == result["status"]


def test_offline_request_does_not_reuse_network_enabled_scan(store, scanned, tmp_path, monkeypatch):
    from veriflow import pipeline
    from veriflow.persistence import ScanAttempt

    path = profile(tmp_path)
    with store.transaction() as session:
        attempt = session.get(ScanAttempt, scanned[2])
        attempt.report = {
            **attempt.report,
            "language": "csharp",
            "language_scope": {
                "adapter_profile": "csharp-source-only-v1",
                "dependency_profile": {"id": load_profile(path)["id"]},
                "network_isolation": "none",
            },
        }
    query = tmp_path / "query.ql"
    query.write_text("// query")

    def preflight(*args):
        raise VeriFlowError("Reached extraction preflight")

    monkeypatch.setattr(pipeline, "verified_source", preflight)
    with pytest.raises(VeriFlowError, match="Reached extraction"):
        pipeline.scan_run(
            store,
            scanned[1],
            query,
            language="csharp",
            skip_existing=True,
            csharp_dependency_profile=path,
            csharp_offline=True,
        )
