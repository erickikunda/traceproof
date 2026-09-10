"""Create the Core fixture profile from reference packs in the pinned SDK archive."""

import json
import shutil
from pathlib import Path

from traceproof.csharp_dependencies import inventory, load_profile

root = Path("/opt/traceproof/csharp-dependencies")
references = root / "core-references"
references.mkdir()
for pack in ("Microsoft.NETCore.App.Ref", "Microsoft.AspNetCore.App.Ref"):
    source = root / "dotnet/packs" / pack / "10.0.0/ref/net10.0"
    shutil.copytree(source, references / pack)
profile = json.loads((root / "profile.json").read_text())
profile["references"] = dict(directory="core-references", files=inventory(references))
output = root / "core-profile.json"
with output.open("x") as handle:
    json.dump(profile, handle, sort_keys=True, indent=2)
load_profile(output)
