"""Produce synthetic source and a local CSV manifest, without scanning or executing it."""

import argparse
import csv
import hashlib
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("work/demo"))
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "synthetic.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(
            "sample/app.py", 'def greet(name: str) -> str:\n    return f"Hello, {name}"\n'
        )
        output.writestr("sample/README.md", "Synthetic TraceProof intake fixture.\n")
    with (root / "repos.csv").open("w", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "repo_id",
                "source_type",
                "source_uri",
                "owner",
                "classification",
                "sha256",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "repo_id": "synthetic-demo",
                "source_type": "pvc",
                "source_uri": str(archive),
                "owner": "poc",
                "classification": "synthetic",
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            }
        )
    print(root / "repos.csv")


if __name__ == "__main__":
    main()
