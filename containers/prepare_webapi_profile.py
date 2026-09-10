"""Create the classic Web API fixture profile from pinned assemblies and net48."""

import json
import shutil
from pathlib import Path

from traceproof.csharp_dependencies import inventory, load_profile

root = Path("/opt/traceproof/csharp-dependencies")
packages = json.loads(Path("/opt/traceproof/webapi-packages.json").read_text())
expected = {Path(member).name: digest for p in packages for member, digest in p["files"].items()}
if inventory(root / "webapi") != expected:
    raise RuntimeError("Web API reference inventory mismatch")
references = root / "webapi-references"
shutil.copytree(root / "net48", references / "net48")
shutil.copytree(root / "webapi", references / "webapi")
profile = json.loads((root / "profile.json").read_text())
profile["references"] = dict(directory="webapi-references", files=inventory(references))
output = root / "webapi-profile.json"
with output.open("x") as handle:
    json.dump(profile, handle, sort_keys=True, indent=2)
load_profile(output)
