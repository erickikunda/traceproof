"""Fail-closed local container acceptance checks; not an OCP attestation."""

import errno
import json
import os
import socket
from pathlib import Path

status = dict(
    line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line
)
assert os.getuid() != 0
assert int(status["CapEff"].strip(), 16) == 0
assert status["NoNewPrivs"].strip() == "1"
try:
    Path("/opt/veriflow/forbidden-write").write_text("probe")
except OSError as exc:
    assert exc.errno in (errno.EROFS, errno.EACCES), exc
else:
    raise AssertionError("Root filesystem was writable")
try:
    socket.create_connection(("1.1.1.1", 443), timeout=2)
except OSError as exc:
    assert exc.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EPERM, errno.EACCES), exc
else:
    raise AssertionError("External network was reachable")
assert not Path("/var/run/docker.sock").exists()
assert not Path("/var/run/secrets/kubernetes.io/serviceaccount/token").exists()
for root in ("/work", "/tmp", "/reports"):
    probe = Path(root) / "veriflow-write-probe"
    probe.write_text("ok")
    probe.unlink()
print(
    json.dumps(
        {
            "passed": True,
            "uid": os.getuid(),
            "capabilities": 0,
            "no_new_privileges": True,
            "external_network_denied": True,
            "scope": "Docker local probe; not OCP qualification",
        }
    )
)
