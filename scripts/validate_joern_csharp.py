"""Opt-in C# flow feasibility. Explicit fixture source; no framework qualification."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from validate_joern import run_stage

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joern-home", type=Path, required=True)
    parser.add_argument("--experimental-classpath", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    home, output = args.joern_home.resolve(), args.output.resolve()
    if not (home / "lib/io.joern.joern-cli-4.0.625.jar").is_file():
        raise RuntimeError("Expected Joern 4.0.625 layout")
    output.mkdir(parents=True, exist_ok=False)
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(output),
        "TMPDIR": str(output),
        "LANG": "en_US.UTF-8",
    }
    if os.environ.get("JAVA_HOME"):
        env["JAVA_HOME"] = os.environ["JAVA_HOME"]
    results = []
    for profile in (
        "csharp-core",
        "csharp-mvc",
        "csharp-webapi",
        "joern-csharp-crossfile",
        "joern-csharp-namespaced",
    ):
        for variant in ("vulnerable", "fixed"):
            source = ROOT / "tests/fixtures" / profile / variant
            case = output / f"{profile}-{variant}"
            case.mkdir()
            hashes = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.cs")
            }
            frontend = [str(home / "csharpsrc2cpg"), "-J-Xmx2g"]
            if args.experimental_classpath:
                frontend = [
                    "java",
                    "-Xmx2g",
                    "-cp",
                    args.experimental_classpath.read_text().strip(),
                    "io.joern.csharpsrc2cpg.Main",
                ]
            prepare = run_stage(
                frontend
                + [
                    str(source),
                    "--output",
                    str(case / "cpg.bin"),
                ],
                case,
                env,
                case / "prepare.log",
            )
            analyze = run_stage(
                [
                    str(home / "joern"),
                    "-J-Xmx2g",
                    "--script",
                    str(ROOT / "scripts/joern/csharp-flow.sc"),
                    "--param",
                    f"cpgFile={case / 'cpg.bin'}",
                    "--param",
                    f"outFile={case / 'flows.json'}",
                ],
                case,
                env,
                case / "analyze.log",
            )
            result = json.loads((case / "flows.json").read_text())
            after = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.cs")
            }
            assert hashes == after
            for flow in result["paths"]:
                for node in flow:
                    path = Path(node["file"])
                    path = path if path.is_absolute() else source / path
                    path = path.resolve(strict=True)
                    assert path.parent == source and path.name in hashes
                    assert 1 <= node["line"] <= len(path.read_text().splitlines())
                    node["line_mapping_verified"] = False
                    node["file"] = path.name
                    node["source_sha256"] = hashes[path.name]
            results.append(
                dict(
                    profile=profile,
                    joern_version="4.0.625",
                    experimental_frontend=bool(args.experimental_classpath),
                    source_sha256=hashes,
                    query_sha256=hashlib.sha256(
                        (ROOT / "scripts/joern/csharp-flow.sc").read_bytes()
                    ).hexdigest(),
                    variant=variant,
                    result=result,
                    preparation_seconds=prepare,
                    analysis_seconds=analyze,
                    passed=(
                        result["flow_count"] > 0
                        if variant == "vulnerable"
                        else result["flow_count"] == 0
                    ),
                )
            )
            (output / "report.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    if not all(item["passed"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
