import os

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from veriflow.cli import app
from veriflow.domain import VeriFlowError
from veriflow.persistence import ScanAttempt
from veriflow.sarif_export import get_sarif


def test_exact_bytes_scope_and_cli(store, scanned):
    repo, _, attempt, _ = scanned
    path = store.root / "scans" / attempt / "results.sarif"
    raw = path.read_bytes()
    assert get_sarif(store, repo, attempt) == raw
    result = CliRunner().invoke(app, ["--state-dir", str(store.root), "get-sarif", repo, attempt])
    assert result.exit_code == 0 and result.stdout_bytes == raw
    with pytest.raises(VeriFlowError, match="belong"):
        get_sarif(store, "other-repo", attempt)
    with store.transaction() as session:
        saved = session.get(ScanAttempt, attempt)
        saved.report = {**saved.report, "status": "partial", "raw_sarif_path": "/ignored"}
    assert get_sarif(store, repo, attempt) == raw


@pytest.mark.parametrize(
    "failure", ["changed", "missing", "symlink", "fifo", "oversized", "failed", "no_digest"]
)
def test_unavailable_or_untrusted_artifact(store, scanned, tmp_path, monkeypatch, failure):
    repo, _, attempt, _ = scanned
    path = store.root / "scans" / attempt / "results.sarif"
    if failure == "changed":
        path.write_bytes(b"private changed source")
    elif failure == "missing":
        path.unlink()
    elif failure == "symlink":
        target = tmp_path / "outside.sarif"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    elif failure == "fifo":
        path.unlink()
        os.mkfifo(path)
    elif failure == "oversized":
        monkeypatch.setattr("veriflow.sarif_export.MAX_SARIF_BYTES", 1)
    else:
        with store.transaction() as session:
            saved = session.get(ScanAttempt, attempt)
            saved.report = {
                **saved.report,
                **({"status": "query_failed"} if failure == "failed" else {"sarif_sha256": None}),
            }
    result = CliRunner().invoke(app, ["--state-dir", str(store.root), "get-sarif", repo, attempt])
    assert result.exit_code == 1 and result.stdout_bytes == b""
    assert "private changed source" not in result.output


def test_parent_link_rejected(store, scanned, tmp_path):
    repo, _, attempt, _ = scanned
    directory = store.root / "scans" / attempt
    moved = tmp_path / "moved"
    directory.rename(moved)
    directory.symlink_to(moved, target_is_directory=True)
    with pytest.raises(VeriFlowError, match="links"):
        get_sarif(store, repo, attempt)
