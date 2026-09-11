"""Build an isolated, pinned C# frontend class override for qualification only."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joern-home", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    home, output = args.joern_home.resolve(), args.output.resolve()
    manifest = json.loads((ROOT / "scripts/joern/csharp-repair/manifest.json").read_text())
    data = args.source.read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest["source_sha256"]:
        raise RuntimeError("Source does not match pinned upstream file")
    patched = data.decode().replace(
        "nonGlobalStatements.flatMap(astForNode)", "astForMembers(nonGlobalStatements)"
    )
    if hashlib.sha256(patched.encode()).hexdigest() != manifest["patched_source_sha256"]:
        raise RuntimeError("Unexpected patched source digest")
    output.mkdir(parents=True, exist_ok=False)
    classes = output / "classes"
    classes.mkdir()
    source = output / "AstCreator.scala"
    source.write_text(patched)
    jars = sorted((home / "frontends/csharpsrc2cpg/lib").glob("*.jar")) + sorted(
        (home / "lib").glob("*.jar")
    )
    if not any(p.name == "io.joern.csharpsrc2cpg-4.0.625.jar" for p in jars):
        raise RuntimeError("Pinned frontend jar missing")
    classpath = os.pathsep.join(map(str, jars))
    with (output / "compile.log").open("w") as log:
        subprocess.run(
            [
                "java",
                "-Xmx2g",
                "-cp",
                classpath,
                "dotty.tools.dotc.Main",
                "-classpath",
                classpath,
                "-d",
                str(classes),
                str(source),
            ],
            stdout=log,
            stderr=log,
            check=True,
            timeout=120,
        )
    (output / "patched-classpath.txt").write_text(str(classes) + os.pathsep + classpath)
    receipt = {
        "manifest": manifest,
        "jar_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in jars},
        "class_sha256": {
            str(p.relative_to(classes)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in classes.rglob("*")
            if p.is_file()
        },
    }
    (output / "build-receipt.json").write_text(json.dumps(receipt, indent=2))
    print(output / "patched-classpath.txt")


if __name__ == "__main__":
    main()
