"""Opt-in source-only JS/TS fixture probe; no production language qualification."""

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from validate_joern import run_stage

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joern-home", type=Path, required=True)
    parser.add_argument("--language", choices=("javascript", "typescript"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    home, output = args.joern_home.resolve(), args.output.resolve()
    release = json.loads((ROOT / "scripts/joern/release.json").read_text())
    if not (home / "lib" / f"io.joern.joern-cli-{release['version']}.jar").is_file():
        raise RuntimeError("Expected pinned Joern version layout not found")
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
    for name in ("vulnerable", "fixed", "crossfile-vulnerable", "crossfile-fixed", "disconnected"):
        case = output / name
        case.mkdir()
        source = case / "source"
        shutil.copytree(ROOT / "tests/fixtures/joern-javascript" / args.language / name, source)
        original = {
            str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source.rglob("*")
            if p.is_file()
        }
        prepare = run_stage(
            [
                str(home / "jssrc2cpg.sh"),
                "-J-Xmx2g",
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
                str(ROOT / "scripts/joern/javascript-flow.sc"),
                "--param",
                f"cpgFile={case / 'cpg.bin'}",
                "--param",
                f"outFile={case / 'flows.json'}",
            ],
            case,
            env,
            case / "analyze.log",
        )
        for path, digest in original.items():
            assert hashlib.sha256((source / path).read_bytes()).hexdigest() == digest
        result = json.loads((case / "flows.json").read_text())
        for flow in result["paths"]:
            for node in flow:
                path = Path(node["file"])
                path = path if path.is_absolute() else source / path
                path = path.resolve(strict=True)
                relative = str(path.relative_to(source))
                assert relative in original
                lines = path.read_text().splitlines()
                assert type(node["line"]) is int and 1 <= node["line"] <= len(lines)
                node["file"] = relative
                node["source_sha256"] = original[relative]
                node["reported_line_contains_code"] = node["code"] in lines[node["line"] - 1]
        results.append(
            dict(
                name=name,
                language=args.language,
                release=release,
                installation_contents_verified=False,
                rule_sha256=hashlib.sha256(
                    (ROOT / "scripts/joern/javascript-flow.sc").read_bytes()
                ).hexdigest(),
                llm_calls=0,
                result=result,
                source_sha256=original,
                preparation_seconds=prepare,
                analysis_seconds=analyze,
                network_isolated=False,
                passed=(
                    result["source_count"] == 1
                    and result["sink_count"] > 0
                    and (
                        result["flow_count"] > 0
                        if name.endswith("vulnerable")
                        else result["flow_count"] == 0
                    )
                ),
            )
        )
        (output / "report.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    if not all(row["passed"] for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
