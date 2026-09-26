import csv
import json

import pytest
from test_git_acquisition import source_repo as source_repo
from typer.testing import CliRunner

from veriflow import git_batch
from veriflow.artifacts import ArtifactStore
from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.intake import process, submit


def manifest(tmp_path, rows):
    path = tmp_path / "repositories.csv"
    with path.open("w", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["repo_id", "url", "revision", "owner", "classification"])
        writer.writerows(rows)
    return path


def row(name="example", url="https://fixture.invalid/repo"):
    return [name, url, "refs/heads/main", "poc", "synthetic"]


def test_real_git_batch_failure_continues_and_intake_binds(tmp_path, source_repo, store):
    path = manifest(
        tmp_path,
        [row("first"), row("bad", "https://user:secret@fixture.invalid/repo"), row("last")],
    )
    output = tmp_path / "output"
    result = git_batch.acquire_csv(path, output, ["fixture.invalid"])
    assert result["state"] == "incomplete" and result["acquired_rows"] == 2
    assert [i["state"] for i in result["items"]] == ["acquired", "failed", "acquired"]
    assert "secret" not in (output / "acquisition-batch.json").read_text()
    batch = submit(store, output / "archives.csv", output, "batch")
    captured = process(store, ArtifactStore(store.root), batch)
    assert [i["state"] for i in captured["items"]] == ["snapshotted", "snapshotted"]
    with pytest.raises(VeriFlowError, match="already exists"):
        git_batch.acquire_csv(path, output, ["fixture.invalid"])


def test_cli_all_valid(tmp_path, source_repo):
    path = manifest(tmp_path, [row()])
    result = CliRunner().invoke(
        app,
        [
            "acquire-git-csv",
            str(path),
            str(tmp_path / "output"),
            "--allowed-host",
            "fixture.invalid",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["state"] == "acquired"


def test_cli_failure_without_usable_csv(tmp_path):
    path = manifest(tmp_path, [row(url="https://unapproved.invalid/repo")])
    result = CliRunner().invoke(
        app,
        [
            "acquire-git-csv",
            str(path),
            str(tmp_path / "output"),
            "--allowed-host",
            "fixture.invalid",
        ],
    )
    assert result.exit_code == 1
    assert not (tmp_path / "output/archives.csv").exists()


def test_batch_limit_before_network(tmp_path, monkeypatch):
    path = manifest(tmp_path, [row(), row()])
    monkeypatch.setattr(git_batch, "acquire", lambda *a, **k: pytest.fail("Unexpected network"))
    with pytest.raises(VeriFlowError):
        git_batch.acquire_csv(path, tmp_path / "output", ["fixture.invalid"], max_rows=1)
    assert not (tmp_path / "output").exists()


def test_deadline_marks_undispatched_rows(tmp_path, monkeypatch):
    path = manifest(tmp_path, [row(), row()])
    ticks = iter([0, 20])
    monkeypatch.setattr(git_batch.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(git_batch, "acquire", lambda *a, **k: pytest.fail("Unexpected network"))
    result = git_batch.acquire_csv(path, tmp_path / "output", ["fixture.invalid"], timeout=10)
    assert result["state"] == "incomplete"
    assert all(i["state"] == "not_started" for i in result["items"])


def test_infrastructure_error_keeps_pending(tmp_path, monkeypatch):
    path = manifest(tmp_path, [row(), row()])

    def fail(*a, **k):
        raise OSError("private diagnostic")

    monkeypatch.setattr(git_batch, "acquire", fail)
    with pytest.raises(OSError):
        git_batch.acquire_csv(path, tmp_path / "output", ["fixture.invalid"])
    result = json.loads((tmp_path / "output/acquisition-batch.json").read_text())
    assert result["state"] == "failed" and result["items"][1]["state"] == "pending"
    assert "private diagnostic" not in json.dumps(result)
