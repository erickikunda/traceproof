"""Local macOS extraction network isolation; no filesystem/build isolation claim."""

import sys
from pathlib import Path

from veriflow.domain import TraceProofError

PROFILE = "(version 1)(allow default)(deny network*)"
MODE = "macos-network-deny-v1"
# Check inside the same sandbox process that execs the target. Unexpected errors,
# timeouts and successful connections all fail closed. No shell interpolation.
GATE = """
import errno, os, socket, sys
try:
    socket.create_connection(('127.0.0.1', 9), timeout=1)
except OSError as exc:
    if exc.errno != errno.EPERM:
        sys.exit(78)
else:
    sys.exit(78)
os.execv(sys.argv[1], sys.argv[1:])
"""


def validate_offline(language, profile, downloads, offline):
    if offline and (language != "csharp" or profile is None or downloads):
        raise TraceProofError(
            "C# offline extraction requires csharp, a dependency profile, "
            "and no allow-csharp-downloads"
        )


def offline_command(command):
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise TraceProofError("C# offline extraction currently requires macOS sandbox-exec")
    return ["/usr/bin/sandbox-exec", "-p", PROFILE, sys.executable, "-c", GATE, *command]
