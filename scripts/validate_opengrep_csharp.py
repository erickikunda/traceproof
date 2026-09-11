"""Opt-in pinned Opengrep C# comparison; not a production backend."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--mode", choices=("intrafile", "interfile"), required=True)
    parser.add_argument("--combined-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binary, output = args.binary.resolve(), args.output.resolve()
    release = next(
        r
        for r in json.loads((ROOT / "scripts/opengrep/releases.json").read_text())
        if r["tag"] == args.tag
    )
    if hashlib.sha256(binary.read_bytes()).hexdigest() != release["sha256"]:
        raise RuntimeError("Binary digest does not match pinned release")
    output.mkdir(parents=True, exist_ok=False)
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(output),
        "TMPDIR": str(output),
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
    }
    rule = ROOT / "scripts/opengrep/csharp-flow.yaml"
    rows = []
    profiles = (
        "csharp-core",
        "csharp-mvc",
        "csharp-webapi",
        "joern-csharp-crossfile",
        "joern-csharp-namespaced",
    )
    if args.combined_only:
        profiles = ("opengrep-csharp-combined",)
    for profile in profiles:
        for variant in ("vulnerable", "fixed"):
            case = output / f"{profile}-{variant}"
            source = case / "source"
            shutil.copytree(ROOT / "tests/fixtures" / profile / variant, source)
            (source / ".semgrepignore").write_text("")
            hashes = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.cs")
            }
            command = [
                str(binary),
                "scan",
                "--config",
                str(rule),
                "--taint-" + args.mode,
                "--dataflow-traces",
                "--json",
                "--disable-version-check",
                "--no-git-ignore",
                ".",
            ]
            started = time.monotonic()
            with (
                (case / "native.json").open("w") as stdout,
                (case / "scan.log").open("w") as stderr,
            ):
                result = subprocess.run(
                    command, cwd=source, env=env, stdout=stdout, stderr=stderr, timeout=120
                )
            native = json.loads((case / "native.json").read_text())
            after = {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*.cs")
            }
            if hashes != after:
                raise RuntimeError("Source changed")
            findings = native.get("results", [])
            scanned = native.get("paths", {}).get("scanned", [])
            locations = []
            for finding in findings:
                path = (source / finding["path"]).resolve()
                path.relative_to(source)
                data = path.read_bytes()
                start, end = finding["start"], finding["end"]
                snippet = data[start["offset"] : end["offset"]].decode()
                locations.append(
                    {
                        "file": path.name,
                        "start": start,
                        "end": end,
                        "snippet": snippet,
                        "start_line_matches_offset": data[: start["offset"]].count(b"\n") + 1
                        == start["line"],
                        "trace": finding.get("extra", {}).get("dataflow_trace"),
                    }
                )
            row = {
                "profile": profile,
                "variant": variant,
                "release": release,
                "mode": args.mode,
                "reported_version": native.get("version"),
                "exit_code": result.returncode,
                "seconds": round(time.monotonic() - started, 3),
                "source_sha256": hashes,
                "rule_sha256": hashlib.sha256(rule.read_bytes()).hexdigest(),
                "scanned": scanned,
                "errors": native.get("errors", []),
                "findings": len(findings),
                "locations": locations,
                "network_isolated": False,
                "llm_calls": 0,
            }
            row["passed"] = (
                result.returncode == 0
                and len(scanned) == len(hashes)
                and not row["errors"]
                and len(findings) == (1 if variant == "vulnerable" else 0)
            )
            rows.append(row)
            (output / "report.json").write_text(json.dumps(rows, indent=2))
    print([(r["profile"], r["variant"], r["findings"], r["passed"]) for r in rows])
    if not all(r["passed"] for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
