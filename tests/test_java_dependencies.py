import csv
import hashlib
import json

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from veriflow.domain import TraceProofError
from veriflow.java_dependencies import java_environment, load_java_profile


def profile(tmp_path):
    relative = "org/example/web/1.0/web-1.0.jar"
    jar = tmp_path / "repository" / relative
    jar.parent.mkdir(parents=True)
    jar.write_bytes(b"synthetic jar")
    path = tmp_path / "java-profile.json"
    path.write_text(
        json.dumps(
            dict(
                version="1",
                codeql_version="2.27.0",
                repository=dict(
                    directory="repository",
                    files={relative: hashlib.sha256(jar.read_bytes()).hexdigest()},
                ),
                artifacts=["org.example:web:jar:1.0"],
            )
        )
    )
    return path, jar


def test_local_classpath_is_generated_without_remote_feed(tmp_path):
    path, _ = profile(tmp_path)
    loaded = load_java_profile(path)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    env = java_environment(loaded, attempt)
    with (attempt / "java-classpath.csv").open() as handle:
        rows = list(csv.reader(handle))
    assert rows == [
        ["org.example:web:jar:1.0", "veriflow-local", (tmp_path / "repository").as_uri()]
    ]
    assert env["CODEQL_EXTRACTOR_JAVA_OPTION_BUILDLESS_DEPENDENCY_DIR"] == str(
        attempt / "java-dependency-cache"
    )


@pytest.mark.parametrize("change", ["modified", "missing", "extra", "symlink"])
def test_inventory_changes_rejected(tmp_path, change):
    path, jar = profile(tmp_path)
    if change == "modified":
        jar.write_bytes(b"changed")
    elif change == "missing":
        jar.unlink()
    elif change == "extra":
        (jar.parent / "extra.jar").touch()
    else:
        jar.unlink()
        jar.symlink_to(path)
    with pytest.raises(TraceProofError):
        load_java_profile(path)


@pytest.mark.parametrize("change", ["escape", "remote", "version", "duplicate", "missing_artifact"])
def test_invalid_profile_rejected(tmp_path, change):
    path, _ = profile(tmp_path)
    data = json.loads(path.read_text())
    if change == "escape":
        data["repository"]["directory"] = "../repository"
    elif change == "remote":
        data["artifacts"] = ["https://example.com/remote.jar"]
    elif change == "version":
        data["codeql_version"] = "unqualified"
    elif change == "duplicate":
        data["artifacts"] *= 2
    else:
        data["artifacts"] = ["org.example:other:jar:1.0"]
    path.write_text(json.dumps(data))
    with pytest.raises(TraceProofError):
        load_java_profile(path)


def test_profile_change_prevents_reuse(store, scanned, tmp_path, monkeypatch):
    from veriflow import pipeline
    from veriflow.persistence import ScanAttempt

    path, _ = profile(tmp_path)
    with store.transaction() as session:
        attempt = session.get(ScanAttempt, scanned[2])
        attempt.report = {
            **attempt.report,
            "language": "java",
            "language_scope": {
                "adapter_profile": "java-dependency-free-v1",
                "java_dependency_profile": {"id": "old"},
            },
        }
    query = tmp_path / "query.ql"
    query.write_text("// query")

    def preflight(*args):
        raise TraceProofError("Reached extraction preflight")

    monkeypatch.setattr(pipeline, "verified_source", preflight)
    with pytest.raises(TraceProofError, match="Reached extraction"):
        pipeline.scan_run(
            store,
            scanned[1],
            query,
            language="java",
            skip_existing=True,
            java_dependency_profile=path,
        )


def test_dependency_mutation_during_extraction_is_not_accepted(
    store, archive, manifest, tmp_path, monkeypatch
):
    import subprocess
    import zipfile

    from test_indexing import captured

    from veriflow.codeql import extract, extraction_status
    from veriflow.persistence import exclusive_worker

    path, jar = profile(tmp_path)
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("C.java", "class C {}")
    run = captured(store, archive, manifest)
    monkeypatch.setattr("veriflow.codeql.build_java_index", lambda *a: {"syntax_gate": "ready"})
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: "/trusted/codeql")
    monkeypatch.setattr(
        "veriflow.codeql.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=b'{"version":"2.27.0"}'),
    )

    class Process:
        def wait(self, timeout):
            jar.write_bytes(b"changed during scan")
            return 0

    def launch(*args, **kwargs):
        assert "CODEQL_JAVA_EXTRACTOR_STANDALONE_CLASSPATH_FILE" in kwargs["env"]
        return Process()

    monkeypatch.setattr("veriflow.codeql.subprocess.Popen", launch)
    with exclusive_worker(store.root):
        result = extract(store, run, language="java", java_dependency_profile=path)
    assert result["status"] == "integrity_failed"
    assert extraction_status(store, result["attempt_id"])["status"] == "integrity_failed"
