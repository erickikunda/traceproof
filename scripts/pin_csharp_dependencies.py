"""Inventory pre-provisioned SDK/reference directories; does not download dependencies.

Example: uv run python scripts/pin_csharp_dependencies.py ROOT --sdk dotnet
--references references/net48 --sdk-version 10.0.100 --codeql-version 2.27.0
The manifest is created once as ROOT/profile.json. Review provenance before pinning.
"""

import argparse
import json
from pathlib import Path, PurePosixPath

from traceproof.csharp_dependencies import inventory, load_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--sdk", required=True)
    parser.add_argument("--references", required=True)
    parser.add_argument("--sdk-version", required=True)
    parser.add_argument("--codeql-version", required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    document = dict(version="1", sdk_version=args.sdk_version, codeql_version=args.codeql_version)
    for key, value in [("sdk", args.sdk), ("references", args.references)]:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            parser.error("SDK/references must be directories beneath ROOT")
        directory = (root / path).resolve(strict=True)
        if not directory.is_relative_to(root) or not directory.is_dir():
            parser.error("Dependency directory must be beneath ROOT")
        document[key] = dict(directory=value, files=inventory(directory))
    output = root / "profile.json"
    with output.open("x") as handle:
        json.dump(document, handle, sort_keys=True, indent=2)
    profile = load_profile(output)
    print(json.dumps({"profile_id": profile["id"], "file_count": profile["file_count"]}))


if __name__ == "__main__":
    main()
