import json
import subprocess
import zipfile

import pytest
from typer.testing import CliRunner

from traceproof import git_acquisition as acquisition
from traceproof.artifacts import ArtifactStore
from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.intake import process, submit


@pytest.mark.parametrize(
    "url,revision,hosts",
    [
        ("http://example.com/repo", "refs/heads/main", ["example.com"]),
        ("https://user:password@example.com/repo", "refs/heads/main", ["example.com"]),
        ("https://example.com/repo?token=x", "refs/heads/main", ["example.com"]),
        ("https://example.com/repo#x", "refs/heads/main", ["example.com"]),
        ("https://example.com/repo", "refs/heads/main", ["other.com"]),
        ("file:///tmp/repo", "refs/heads/main", ["example.com"]),
        ("https://example.com/repo", "--upload-pack=evil", ["example.com"]),
        ("https://example.com/repo", "main", ["example.com"]),
        ("https://example.com/repo", "refs/heads/../x", ["example.com"]),
    ],
)
def test_invalid_source_rejected_before_output(tmp_path, url, revision, hosts):
    with pytest.raises(TraceProofError):
        acquisition.acquire(url, revision, hosts, tmp_path / "out", "example", "poc", "synthetic")
    assert not (tmp_path / "out").exists()


@pytest.fixture
def source_repo(tmp_path, monkeypatch):
    root = tmp_path / "remote"
    root.mkdir()

    def git(*args):
        return (
            subprocess.check_output(
                [
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    *args,
                ],
                cwd=root,
            )
            .decode()
            .strip()
        )

    git("init", "-q", "-b", "main")
    (root / "app.py").write_text('print("fixture")\n')
    (root / ".gitattributes").write_text("app.py export-ignore\n*.py filter=malicious\n")
    git("add", ".")
    git("commit", "-qm", "fixture")
    commit = git("rev-parse", "HEAD")
    original = acquisition.Git.call

    def local_transport(self, *args, **kwargs):
        # Only the test fetch transport changes; all production Git isolation/export code runs.
        if "fetch" in args:
            args = tuple(str(root) if a == "https://fixture.invalid/repo" else a for a in args)
            old = self.command
            self.command = old + ["-c", "protocol.file.allow=always"]
            try:
                return original(self, *args, **kwargs)
            finally:
                self.command = old
        return original(self, *args, **kwargs)

    monkeypatch.setattr(acquisition.Git, "call", local_transport)
    return root, git, commit


def run(output):
    return acquisition.acquire(
        "https://fixture.invalid/repo",
        "refs/heads/main",
        ["fixture.invalid"],
        output,
        "example",
        "poc",
        "synthetic",
    )


def test_real_git_raw_export_and_existing_intake(tmp_path, source_repo, store, monkeypatch):
    root, git, commit = source_repo
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "never")
    output = tmp_path / "out"
    result = run(output)
    assert result["resolved_commit"] == commit and result["state"] == "acquired"
    with zipfile.ZipFile(output / "source.zip") as archive:
        assert archive.read("app.py") == b'print("fixture")\n'
        assert ".gitattributes" in archive.namelist()
    batch = submit(store, output / "input.csv", output, "git-acquired")
    imported = process(store, ArtifactStore(store.root), batch)
    assert imported["items"][0]["state"] == "snapshotted"
    with pytest.raises(TraceProofError, match="already exists"):
        run(output)
    assert json.loads((output / "acquisition.json").read_text()) == result
    (root / "app.py").write_text('print("next")\n')
    git("add", ".")
    git("commit", "-qm", "next")
    assert run(tmp_path / "second")["resolved_commit"] != commit


@pytest.mark.parametrize("kind", ["symlink", "lfs", "submodule", "oversize"])
def test_unsupported_content_never_publishes_csv(tmp_path, source_repo, monkeypatch, kind):
    root, git, commit = source_repo
    if kind == "symlink":
        (root / "link").symlink_to("app.py")
    elif kind == "lfs":
        (root / "large").write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\n")
    elif kind == "submodule":
        git("update-index", "--add", "--cacheinfo", f"160000,{commit},nested")
    else:
        monkeypatch.setattr(acquisition, "MAX_FILE_BYTES", 1)
    if kind != "submodule":
        git("add", ".")
    git("commit", "--allow-empty", "-qm", "unsupported")
    output = tmp_path / "out"
    with pytest.raises(TraceProofError):
        run(output)
    assert not (output / "input.csv").exists()
    assert not (output / "source.zip").exists()
    assert json.loads((output / "acquisition.json").read_text())["state"] == "failed"
    assert not list(output.glob(".git-acquire-*"))


def test_cli_rejects_unapproved_host(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "acquire-git",
            "https://example.com/repo",
            "refs/heads/main",
            str(tmp_path / "out"),
            "example",
            "poc",
            "synthetic",
            "--allowed-host",
            "other.com",
        ],
    )
    assert result.exit_code == 1
    assert "explicitly allowed host" in result.output


def test_command_timeout_terminates_child(tmp_path):
    import sys

    worker = acquisition.Git(tmp_path, 1)
    worker.command = [sys.executable, "-c", "import time; time.sleep(10)"]
    with pytest.raises(TraceProofError, match="limit"):
        worker.call()


def test_command_output_limit(tmp_path):
    import sys

    worker = acquisition.Git(tmp_path, 5)
    worker.command = [sys.executable, "-c", 'print("x" * 10000)']
    with pytest.raises(TraceProofError, match="limit"):
        worker.call(limit=100)
