"""Create the classic framework fixture profile from pinned assemblies and net48."""

import argparse
import json
import shutil
from pathlib import Path

from traceproof.csharp_dependencies import inventory, load_profile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("family", choices=("webapi", "mvc"))
family = parser.parse_args().family

root = Path("/opt/traceproof/csharp-dependencies")
packages = json.loads(Path(f"/opt/traceproof/{family}-packages.json").read_text())
expected = {Path(member).name: digest for p in packages for member, digest in p["files"].items()}
if inventory(root / family) != expected:
    raise RuntimeError("Classic framework reference inventory mismatch")
references = root / f"{family}-references"
shutil.copytree(root / "net48", references / "net48")
shutil.copytree(root / family, references / family)
profile = json.loads((root / "profile.json").read_text())
profile["references"] = dict(directory=f"{family}-references", files=inventory(references))
output = root / f"{family}-profile.json"
with output.open("x") as handle:
    json.dump(profile, handle, sort_keys=True, indent=2)
load_profile(output)
