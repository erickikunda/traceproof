"""Run real Python acceptance in a restricted Linux container and export its reports."""

import argparse
import json
import subprocess
import time
import uuid
from pathlib import Path

QUERY = (
    "/opt/codeql-bundle/codeql/qlpacks/codeql/python-queries/1.8.10/"
    "Security/CWE-094/CodeInjection.ql"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New local output directory")
    parser.add_argument("--image", default="traceproof:linux-poc")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    name = "traceproof-smoke-" + uuid.uuid4().hex[:12]
    inspected = json.loads(subprocess.check_output(["docker", "image", "inspect", args.image]))[0]
    if inspected["Architecture"] != "arm64" or inspected["Os"] != "linux":
        raise RuntimeError("This acceptance recipe requires a Linux ARM64 image")
    image = inspected["Id"]  # Run the inspected immutable local image ID, not a moving tag.
    command = [
        "docker",
        "create",
        "--name",
        name,
        "--platform",
        "linux/arm64",
        "--user",
        "1000710000:0",
        "--read-only",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--cpus",
        "2",
        "--memory",
        "4g",
        "--pids-limit",
        "256",
        "--tmpfs",
        "/work:rw,exec,nosuid,nodev,size=1073741824,mode=0770,gid=0",
        "--tmpfs",
        "/tmp:rw,exec,nosuid,nodev,size=1073741824,mode=1777",
        "--mount",
        f"type=bind,src={output},dst=/reports",
        "--entrypoint",
        "/bin/bash",
        image,
        "-euc",
        "mkdir /reports/diagnostics\n"
        'trap \'find /work -name "*.log" '
        "-exec cp --parents {} /reports/diagnostics/ \\; || true' EXIT\n"
        "python /opt/traceproof/runtime_probe.py > /reports/runtime.json\n"
        "python -m pip inspect > /reports/python-packages.json\n"
        "rpm -qa | sort > /reports/os-packages.txt\n"
        f"traceproof acceptance-run /work/acceptance {QUERY} "
        "--timeout 300 > /reports/cli.log 2>&1\n"
        "cp /work/acceptance/acceptance.json /reports/\n"
        "cp /work/acceptance/*.html /work/acceptance/*.csv /work/acceptance/*.md /reports/\n"
        "cp /work/acceptance/vulnerable.json /work/acceptance/fixed.json "
        "/work/acceptance/incomplete.json /reports/\n",
    ]
    subprocess.run(command, check=True, capture_output=True)
    started = time.monotonic()
    try:
        (output / "container-config.json").write_bytes(
            subprocess.check_output(["docker", "inspect", name])
        )
        try:
            result = subprocess.run(["docker", "start", "-a", name], timeout=900)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], check=False, capture_output=True)
            raise
        finally:
            state = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]["State"]
            (output / "container-state.json").write_text(json.dumps(state, indent=2))
        passed = result.returncode == 0 and (output / "acceptance.json").exists()
        if passed:
            passed = json.loads((output / "acceptance.json").read_text())["passed"]
        summary = dict(
            passed=passed,
            image_id=image,
            architecture=inspected["Architecture"],
            elapsed_seconds=round(time.monotonic() - started, 3),
            ocp_qualified=False,
            scope="Local restricted Linux Python fixture validation",
        )
        (output / "validation.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary))
        if not passed:
            raise SystemExit("Container acceptance failed; inspect output diagnostics")
    finally:
        subprocess.run(["docker", "rm", "--force", name], check=False, capture_output=True)


if __name__ == "__main__":
    main()
