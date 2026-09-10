import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture

from traceproof import codeql, scanning
from traceproof.codeql_resources import resource_settings
from traceproof.domain import TraceProofError
from traceproof.persistence import ScanAttempt


@pytest.mark.parametrize(
    "threads,ram",
    [(0, 2048), (-1, 2048), (65, 2048), (True, 2048), (2, 2047), (2, 262145), (2, 2048.0)],
)
def test_invalid_resources_rejected_before_storage(threads, ram):
    with pytest.raises(TraceProofError):
        codeql.extract(None, "unused", threads=threads, ram_mb=ram)
    with pytest.raises(TraceProofError):
        scanning.analyze(None, "unused", None, threads=threads, ram_mb=ram)


def test_command_settings_and_durable_records(store, scanned, tmp_path, monkeypatch):
    _, run, old_attempt, _ = scanned
    raw = (store.root / "scans" / old_attempt / "results.sarif").read_bytes()
    commands = []
    monkeypatch.setattr(codeql.shutil, "which", lambda name: "/operator/codeql")
    monkeypatch.setattr(
        codeql.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(stdout=json.dumps({"version": "synthetic"}).encode()),
    )

    def launch(command, **kwargs):
        commands.append(command)
        for arg in command:
            if arg.startswith("--output="):
                Path(arg.split("=", 1)[1]).write_bytes(raw)
        return SimpleNamespace(wait=lambda timeout: 0)

    monkeypatch.setattr(codeql.subprocess, "Popen", launch)
    extracted = codeql.extract(store, run, threads=3, ram_mb=4096)
    assert extracted["status"] == "extracted"
    assert codeql.extraction_status(store, extracted["attempt_id"])["requested_resources"] == {
        "threads": 3,
        "ram_mb": 4096,
    }
    query = tmp_path / "approved.ql"
    query.write_text("// synthetic")
    analyzed = scanning.analyze(store, extracted["attempt_id"], query, threads=1, ram_mb=8192)
    with store.transaction() as session:
        assert session.get(ScanAttempt, analyzed["attempt_id"]).report["requested_resources"] == {
            "threads": 1,
            "ram_mb": 8192,
        }
    assert "--threads=3" in commands[0] and "--ram=4096" in commands[0]
    assert "--threads=1" in commands[1] and "--ram=8192" in commands[1]
    assert resource_settings() == {"threads": 2, "ram_mb": 2048}
