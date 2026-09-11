"""Opt-in dependency-free Cargo fixture probe; no production Rust qualification."""

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
    parser.add_argument("--rust-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    home, rust, output = args.joern_home.resolve(), args.rust_home.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = {
        "PATH": str(rust / "bin") + os.pathsep + os.environ.get("PATH", os.defpath),
        "HOME": str(output),
        "TMPDIR": str(output),
        "LANG": "en_US.UTF-8",
        "CARGO_HOME": str(output / "cargo-home"),
        "CARGO_NET_OFFLINE": "true",
    }
    if os.environ.get("JAVA_HOME"):
        env["JAVA_HOME"] = os.environ["JAVA_HOME"]
    results = []
    for name in ("vulnerable", "fixed", "crossfile-vulnerable", "crossfile-fixed"):
        case = output / name
        case.mkdir()
        source = case / "source"
        shutil.copytree(ROOT / "tests/fixtures/joern-rust" / name, source)
        original = {
            str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source.rglob("*")
            if p.is_file()
        }
        prepare = run_stage(
            [str(home / "rust2cpg"), "-J-Xmx2g", str(source), "--output", str(case / "cpg.bin")],
            case,
            env,
            case / "prepare.log",
        )
        analyze = run_stage(
            [
                str(home / "joern"),
                "-J-Xmx2g",
                "--script",
                str(ROOT / "scripts/joern/rust-flow.sc"),
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
                result=result,
                source_sha256=original,
                preparation_seconds=prepare,
                analysis_seconds=analyze,
                network_isolated=False,
                cargo_offline=True,
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
