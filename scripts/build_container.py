"""Build the pinned ARM64 Linux POC image. Downloads only in this preparation step."""

import argparse
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="traceproof:linux-poc")
    args = parser.parse_args()
    lock = json.loads((ROOT / "containers/toolchain.json").read_text())
    for name in ("codeql", "jdk"):
        archive = ROOT / f"work/container-inputs/{name}-linux-arm64.tar.gz"
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            temporary = archive.with_suffix(".download")
            urllib.request.urlretrieve(lock[name + "_url"], temporary)
            with temporary.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            if digest != lock[name + "_sha256"]:
                raise RuntimeError("Toolchain download checksum mismatch")
            temporary.replace(archive)
        with archive.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != lock[name + "_sha256"]:
                raise RuntimeError("Cached Toolchain checksum mismatch")
    subprocess.run(["uv", "build"], cwd=ROOT, check=True)
    subprocess.run(
        [
            "docker",
            "build",
            "--platform",
            lock["platform"],
            "--build-arg",
            "CODEQL_SHA256=" + lock["codeql_sha256"],
            "--build-arg",
            "JDK_SHA256=" + lock["jdk_sha256"],
            "-f",
            "containers/Containerfile",
            "-t",
            args.tag,
            ".",
        ],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
