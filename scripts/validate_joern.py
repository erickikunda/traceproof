"""Opt-in local synthetic Java feasibility probe; not a production scanner adapter."""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_stage(command, cwd, env, log):
    started = time.monotonic()
    with log.open("wb") as output:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=output,
            stderr=output,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise RuntimeError(f"Joern stage timed out; see {log}") from None
    if code:
        raise RuntimeError(f"Joern stage exited {code}; see {log}")
    return round(time.monotonic() - started, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joern-home", type=Path, required=True)
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
    report = {
        "schema_version": "1",
        "engine_id": "joern",
        "release": release,
        "installation_contents_verified": False,
        "java_runtime": subprocess.run(
            ["java", "-version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stderr.strip(),
        "cases": [],
        "qualification": "synthetic_fixture_only",
        "network_isolated": False,
        "llm_calls": 0,
        "rule_sha256": hashlib.sha256(
            (ROOT / "src/traceproof/queries/joern-java-flow.sc").read_bytes()
        ).hexdigest(),
    }
    expected = {
        "vulnerable": 1,
        "fixed": 0,
        "disconnected": 0,
        "renamed": 1,
        "annotation-lookalike": 0,
        "sink-lookalike": 0,
        "unmapped-route": 0,
    }
    for name in expected:
        case = output / name
        case.mkdir()
        source = ROOT / "tests/fixtures/joern-java" / name
        source_hashes = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source.glob("*.java"))
        }
        cpg = case / "cpg.bin"
        preparation = run_stage(
            [str(home / "javasrc2cpg"), "-J-Xmx2g", str(source), "--output", str(cpg)],
            case,
            env,
            case / "prepare.log",
        )
        analysis = run_stage(
            [
                str(home / "joern"),
                "-J-Xmx2g",
                "--script",
                str(ROOT / "src/traceproof/queries/joern-java-flow.sc"),
                "--param",
                f"cpgFile={cpg}",
                "--param",
                f"outFile={case / 'flows.json'}",
            ],
            case,
            env,
            case / "analyze.log",
        )
        result = json.loads((case / "flows.json").read_text())
        after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source.glob("*.java"))
        }
        if source_hashes != after:
            raise RuntimeError("Fixture source changed during analysis")
        for flow in result["paths"]:
            for node in flow:
                file = Path(node["file"])
                file = file if file.is_absolute() else source / file
                file = file.resolve(strict=True)
                if file.parent != source.resolve() or file.name not in source_hashes:
                    raise RuntimeError("Flow references unexpected fixture source")
                if not 1 <= node["line"] <= len(file.read_text().splitlines()):
                    raise RuntimeError("Flow has invalid source line")
                node["file"] = file.name
                node["source_sha256"] = source_hashes[file.name]
        report["cases"].append(
            {
                "name": name,
                "source_sha256": source_hashes,
                "preparation_seconds": preparation,
                "analysis_seconds": analysis,
                "result": result,
            }
        )
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    report["fixture_expectations_met"] = all(
        case["result"]["flow_count"] == expected[case["name"]] for case in report["cases"]
    )
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["fixture_expectations_met"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
