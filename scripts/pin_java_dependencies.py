"""Pin a pre-provisioned local Maven-layout JAR repository; performs no downloads."""

import argparse
import json
import tempfile
from pathlib import Path

from veriflow.csharp_dependencies import inventory
from veriflow.java_dependencies import load_java_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--repository", required=True, help="Directory beneath root")
    parser.add_argument("--artifact", action="append", required=True, help="group:name:jar:version")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    repo = (root / args.repository).resolve(strict=True)
    if not repo.is_relative_to(root) or not repo.is_dir():
        parser.error("Repository must be a directory beneath root")
    target = root / "java-profile.json"
    data = dict(
        version="1",
        codeql_version="2.27.0",
        repository=dict(directory=repo.relative_to(root).as_posix(), files=inventory(repo)),
        artifacts=args.artifact,
    )
    raw = json.dumps(data, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", dir=root, suffix=".json") as temporary:
        temporary.write(raw)
        temporary.flush()
        load_java_profile(temporary.name)
        with target.open("x") as handle:
            handle.write(raw)
    print(target)


if __name__ == "__main__":
    main()
