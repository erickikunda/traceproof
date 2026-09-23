import subprocess
import sys

import pytest

from veriflow.domain import TraceProofError
from veriflow.network_isolation import offline_command, validate_offline


@pytest.mark.parametrize(
    "language,profile,downloads",
    [("python", "p", False), ("csharp", None, False), ("csharp", "p", True)],
)
def test_offline_requires_unambiguous_pinned_csharp(language, profile, downloads):
    with pytest.raises(TraceProofError):
        validate_offline(language, profile, downloads, True)


def test_unsupported_host_fails_closed(monkeypatch):
    monkeypatch.setattr("veriflow.network_isolation.sys.platform", "linux")
    with pytest.raises(TraceProofError, match="macOS"):
        offline_command(["/usr/bin/true"])


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS qualification")
def test_real_offline_gate_denies_target_and_child_connections():
    # Permission denial must survive exec and another generation of child processes.
    code = """
import subprocess, sys
probe = "import socket; socket.create_connection(('127.0.0.1', 9), timeout=1)"
r = subprocess.run([sys.executable, '-c', probe], capture_output=True, text=True)
assert r.returncode != 0 and 'PermissionError: [Errno 1]' in r.stderr, r.stderr
"""
    result = subprocess.run(
        offline_command([sys.executable, "-c", code]), capture_output=True, timeout=10
    )
    assert result.returncode == 0, result.stderr


def test_gate_refuses_to_execute_when_network_not_denied(tmp_path):
    from veriflow.network_isolation import GATE

    marker = tmp_path / "executed"
    # Substitute only the probe to simulate unexpectedly working network access.
    gate = GATE.replace("socket.create_connection(('127.0.0.1', 9), timeout=1)", "None")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            gate,
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).touch()",
        ],
        timeout=10,
    )
    assert result.returncode == 78
    assert not marker.exists()
