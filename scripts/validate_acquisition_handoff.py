"""Public HTTPS acquisition then offline scan; no credentials, push or cluster access."""

import argparse
import csv
import json
import subprocess
from pathlib import Path


def identity(tag):
    return json.loads(subprocess.check_output(["docker", "image", "inspect", tag]))[0]


def runtime(image, mounts, network):
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
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
        "/work:rw,exec,nosuid,nodev,size=2g,mode=1777",
        "--tmpfs",
        "/tmp:rw,exec,nosuid,nodev,size=1g,mode=1777",
        *mounts,
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-image", required=True)
    parser.add_argument("--scanner-image", required=True)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    for name in ["input", "handoff", "reports"]:
        (root / name).mkdir()
        (root / name).chmod(0o777)
    with (root / "input/repositories.csv").open("w") as target:
        writer = csv.writer(target)
        writer.writerow(["repo_id", "url", "revision", "owner", "classification"])
        writer.writerow(
            ["jsmn", "https://github.com/zserge/jsmn.git", "refs/heads/master", "poc", "public"]
        )
        writer.writerow(
            ["denied", "https://unapproved.invalid/repo", "refs/heads/main", "poc", "public"]
        )
    acquire_image = identity(args.acquisition_image)
    scan_image = identity(args.scanner_image)
    assert acquire_image["Os"] == "linux" and acquire_image["Architecture"] == "arm64"
    assert scan_image["Os"] == "linux" and scan_image["Architecture"] == "arm64"
    common = runtime(
        acquire_image["Id"],
        [
            "--mount",
            f"type=bind,source={root / 'input'},target=/input,readonly",
            "--mount",
            f"type=bind,source={root / 'handoff'},target=/handoff",
        ],
        "bridge",
    )
    # Prove image separation; this read-only command does not start any scanner.
    check = subprocess.run(
        common
        + [
            "--entrypoint",
            "/bin/bash",
            acquire_image["Id"],
            "-ec",
            "test ! -e /opt/joern-cli; test ! -e /opt/codeql-bundle; "
            "test ! -e /opt/jdk; test ! -e /opt/rust; git --version; "
            "cat /opt/traceproof/application-inputs.sha256",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert check.returncode == 0, check.stderr
    (root / "acquisition-image.txt").write_text(check.stdout)
    acquired = subprocess.run(
        common
        + [
            acquire_image["Id"],
            "/input/repositories.csv",
            "/handoff/batch",
            "--allowed-host",
            "github.com",
            "--max-rows",
            "2",
            "--timeout",
            "300",
        ],
        capture_output=True,
        text=True,
        timeout=360,
    )
    (root / "acquire.log").write_text(acquired.stdout + acquired.stderr)
    assert acquired.returncode == 1, acquired.stdout + acquired.stderr
    summary = json.loads((root / "handoff/batch/acquisition-batch.json").read_text())
    assert summary["state"] == "incomplete" and summary["acquired_rows"] == 1
    assert [i["state"] for i in summary["items"]] == ["acquired", "failed"]
    mounts = [
        "--mount",
        f"type=bind,source={root / 'handoff'},target=/handoff,readonly",
        "--mount",
        f"type=bind,source={root / 'reports'},target=/reports",
    ]
    offline = runtime(scan_image["Id"], mounts, "none")
    probe = subprocess.run(
        offline
        + [
            "--entrypoint",
            "/opt/traceproof-venv/bin/python",
            scan_image["Id"],
            "/opt/traceproof/runtime_probe.py",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    (root / "offline-probe.json").write_text(probe.stdout)
    assert probe.returncode == 0, probe.stderr
    scanned = subprocess.run(
        offline
        + [
            "-e",
            "TRACEPROOF_EXECUTION_ID=offline-scan",
            "--entrypoint",
            "/opt/traceproof-venv/bin/python",
            scan_image["Id"],
            "/opt/traceproof/ocp_archive_batch.py",
            "--input",
            "/handoff/batch",
            "--language",
            "c",
            "--max-rows",
            "2",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    (root / "scan.log").write_text(scanned.stdout + scanned.stderr)
    assert scanned.returncode == 0, scanned.stdout + scanned.stderr
    batch = json.loads((root / "reports/offline-scan/batch.json").read_text())
    assert batch["state"] == "exported" and len(batch["items"]) == 1
    report = json.loads(
        (root / "reports/offline-scan" / batch["items"][0]["report_path"]).read_text()
    )
    assert report["acquisition_provenance"]["state"] == "snapshot_bound"
    assert (
        report["acquisition_provenance"]["resolved_commit"]
        == summary["items"][0]["resolved_commit"]
    )
    assert report["static_review_readiness"]["state"] == "incomplete"
    final = dict(
        passed=True,
        acquisition_image=acquire_image["Id"],
        scanner_image=scan_image["Id"],
        resolved_commit=summary["items"][0]["resolved_commit"],
        acquisition_state="incomplete",
        scan_subset_state="exported",
        report_id=report["report_id"],
        candidate_count=report["candidate_count"],
        model_calls=0,
        ocp_qualified=False,
        scope="Public repository handoff; not a quality benchmark",
    )
    (root / "validation.json").write_text(json.dumps(final, indent=2))
    print(json.dumps(final))


if __name__ == "__main__":
    main()
