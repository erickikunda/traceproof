"""Build the pinned ARM64 Linux POC image. Downloads only in this preparation step."""

import argparse
import hashlib
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="traceproof:linux-poc")
    args = parser.parse_args()
    lock = json.loads((ROOT / "containers/toolchain.json").read_text())
    for name, algorithm in (("codeql", "sha256"), ("jdk", "sha256"), ("dotnet", "sha512")):
        archive = ROOT / f"work/container-inputs/{name}-linux-arm64.tar.gz"
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            temporary = archive.with_suffix(".download")
            urllib.request.urlretrieve(lock[name + "_url"], temporary)
            with temporary.open("rb") as handle:
                digest = hashlib.file_digest(handle, algorithm).hexdigest()
            if digest != lock[name + "_" + algorithm]:
                raise RuntimeError("Toolchain download checksum mismatch")
            temporary.replace(archive)
        with archive.open("rb") as handle:
            if hashlib.file_digest(handle, algorithm).hexdigest() != lock[name + "_" + algorithm]:
                raise RuntimeError("Cached Toolchain checksum mismatch")
    package = ROOT / "work/container-inputs/net48.nupkg"
    if not package.exists():
        urllib.request.urlretrieve(lock["net48_url"], package)
    if hashlib.sha256(package.read_bytes()).hexdigest() != lock["net48_sha256"]:
        raise RuntimeError("Reference assembly package checksum mismatch")
    references = ROOT / "work/container-inputs/net48"
    if references.exists():
        import shutil

        shutil.rmtree(references)
    references.mkdir()
    with zipfile.ZipFile(package) as archive:
        prefix = "build/.NETFramework/v4.8/"
        for member in archive.namelist():
            if member.startswith(prefix) and member.lower().endswith(".dll"):
                relative = Path(member[len(prefix) :])
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError("Unsafe reference assembly path")
                target = references / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))
    profile = json.loads((ROOT / "containers/java-profile.json").read_text())
    repository = ROOT / "work/container-inputs/java-repository"
    for relative, expected in profile["repository"]["files"].items():
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary = target.with_suffix(".download")
            urllib.request.urlretrieve(
                "https://repo.maven.apache.org/maven2/" + relative, temporary
            )
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
                raise RuntimeError("Java dependency checksum mismatch")
            temporary.replace(target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Cached Java dependency checksum mismatch")
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
            "--build-arg",
            "DOTNET_SHA512=" + lock["dotnet_sha512"],
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
