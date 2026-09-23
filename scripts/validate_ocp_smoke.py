"""Local Docker rehearsal of the OCP smoke entrypoint; no cluster access."""

import argparse
import csv
import json
import subprocess
import zipfile
from pathlib import Path

FIXTURES = {
    "csharp": "csharp-core",
    "rust": "joern-rust-env",
    "java": "joern-java",
    "python": "joern-flask",
    "javascript": "joern-express/javascript",
    "typescript": "joern-express/typescript",
    "go": "joern-go-http",
    "c": "joern-argv/c",
    "cpp": "joern-argv/cpp",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("output", type=Path)
    parser.add_argument("--language", choices=sorted(FIXTURES), default="c")
    parser.add_argument(
        "--manifest-name", choices=["archives.csv", "input.csv"], default="archives.csv"
    )
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    inputs, reports = root / "input", root / "reports"
    inputs.mkdir()
    reports.mkdir(mode=0o777)
    reports.chmod(0o777)  # Local Docker Desktop rehearsal only; OCP uses SCC/storage policy.
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures" / FIXTURES[args.language]
    image = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", args.image], text=True
    ).strip()
    results = []
    for case, expected in (("vulnerable", 1), ("fixed", 0)):
        with zipfile.ZipFile(inputs / "source.zip", "w") as archive:
            for file in (fixtures / case).rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(fixtures / case))
        with (inputs / args.manifest_name).open("w") as file:
            writer = csv.writer(file)
            writer.writerow(["repo_id", "source_type", "source_uri", "owner", "classification"])
            writer.writerow([case, "pvc", "/input/source.zip", "poc", "synthetic"])
        base = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--user",
            "1000710000:0",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--cpus",
            "2",
            "--memory",
            "4g",
            "--pids-limit",
            "512",
            "--tmpfs",
            "/work:rw,exec,nosuid,nodev,size=6g,mode=1777",
            "--tmpfs",
            "/tmp:rw,exec,nosuid,nodev,size=1g,mode=1777",
            "--mount",
            f"type=bind,source={inputs},target=/input,readonly",
            "--mount",
            f"type=bind,source={reports},target=/reports",
        ]
        probe = subprocess.run(
            base
            + [
                "--entrypoint",
                "/opt/veriflow-venv/bin/python",
                image,
                "/opt/veriflow/runtime_probe.py",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        (root / f"{case}-probe.log").write_text(probe.stdout + probe.stderr)
        if probe.returncode:
            raise RuntimeError("Restricted runtime probe failed")
        command = base + [
            "-e",
            f"TRACEPROOF_EXECUTION_ID={case}",
            image,
            "--language",
            args.language,
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        (root / f"{case}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("Smoke entrypoint failed; inspect local artifacts")
        status = json.loads((reports / case / "result.json").read_text())
        report = json.loads((reports / case / "report.json").read_text())
        assert status["state"] == "exported"
        assert status["manifest_name"] == args.manifest_name
        assert status["model_calls"] == 0 and status["ocp_qualified"] is False
        assert report["report_id"] == status["report_id"]
        assert report["candidate_count"] == expected
        assert report["language"] == args.language
        assert status["language"] == args.language
        assert report["discovery_profile"] == status["discovery_profile"]
        assert report["static_review_readiness"]["state"] == "incomplete"
        assert (reports / case / "report.html").stat().st_size > 0
        results.append(
            {
                "case": case,
                "passed": True,
                "candidate_count": expected,
                "report_id": report["report_id"],
            }
        )
    summary = {
        "passed": True,
        "image_id": image,
        "ocp_qualified": False,
        "scope": "Local Docker entrypoint rehearsal",
        "language": args.language,
        "manifest_name": args.manifest_name,
        "cases": results,
    }
    (root / "validation.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
