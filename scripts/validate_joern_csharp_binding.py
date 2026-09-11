"""Adversarial fixture call-binding checks for the experimental C# repair."""

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
    parser.add_argument("--experimental-classpath", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    home, output = args.joern_home.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(output),
        "TMPDIR": str(output),
        "LANG": "en_US.UTF-8",
    }
    fixture = ROOT / "tests/fixtures/joern-csharp-binding"
    query = ROOT / "scripts/joern/csharp-binding.sc"
    rows = []
    for spec in json.loads((fixture / "cases.json").read_text()):
        case = output / spec["name"]
        source = case / "source"
        shutil.copytree(fixture / spec["name"], source)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.cs")}
        prepare = run_stage(
            [
                "java",
                "-Xmx2g",
                "-cp",
                args.experimental_classpath.read_text().strip(),
                "io.joern.csharpsrc2cpg.Main",
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
                str(query),
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
        assert hashes == {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.cs")
        }
        expected = spec["expected_owner"] + ".Find:DbDataReader(System.String,DbConnection)"
        binding_ok = (
            len(result["bindings"]) == 1
            and result["bindings"][0]["callees"] == [expected]
            and result["bindings"][0]["method_full_name"] == expected
        )
        flow_ok = (
            result["source_count"] == 1
            and result["sink_count"] == 1
            and result["flow_count"] == (1 if spec["positive"] else 0)
        )
        rows.append(
            {
                "case": spec,
                "expected_callee": expected,
                "binding_passed": binding_ok,
                "flow_passed": flow_ok,
                "passed": binding_ok and flow_ok,
                "source_sha256": hashes,
                "query_sha256": hashlib.sha256(query.read_bytes()).hexdigest(),
                "experimental_classpath_sha256": hashlib.sha256(
                    args.experimental_classpath.read_bytes()
                ).hexdigest(),
                "result": result,
                "preparation_seconds": prepare,
                "analysis_seconds": analyze,
                "qualification": "experimental_fixture_only",
                "network_isolated": False,
            }
        )
        (output / "report.json").write_text(json.dumps(rows, indent=2))
    print([(r["case"]["name"], r["flow_passed"], r["binding_passed"]) for r in rows])
    if not all(r["passed"] for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
