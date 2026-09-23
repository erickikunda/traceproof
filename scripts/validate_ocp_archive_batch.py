"""Real mounted batch rehearsal, with successful and mixed-failure input sets."""

import argparse
import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


def fixture_receipt(inputs, case):
    """Synthetic source assertions only; no claim of real remote Git acquisition."""
    entries = []
    with zipfile.ZipFile(inputs / f"{case}.zip") as archive:
        for name in archive.namelist():
            data = archive.read(name)
            entries.append(
                dict(
                    path=name,
                    size_bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),
                    git_blob=hashlib.sha1(
                        b"blob " + str(len(data)).encode() + b"\0" + data
                    ).hexdigest(),
                )
            )
    archive_sha = hashlib.sha256((inputs / f"{case}.zip").read_bytes()).hexdigest()
    receipt = dict(
        schema_version="1",
        state="acquired",
        url="https://fixture.invalid/synthetic",
        requested_revision="refs/heads/fixture",
        repo_id=case,
        model_calls=0,
        coverage_verified=False,
        resolved_commit="a" * 40,
        git_version="synthetic fixture",
        archive_sha256=archive_sha,
        files=entries,
        source_bytes=sum(f["size_bytes"] for f in entries),
        omissions=[],
        limitations=["Synthetic provenance record; not an actual Git acquisition"],
    )
    raw = json.dumps(receipt).encode()
    (inputs / f"{case}.receipt.json").write_bytes(raw)
    return [archive_sha, f"/input/{case}.receipt.json", hashlib.sha256(raw).hexdigest()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--language", choices=["c", "csharp", "rust"], default="c")
    parser.add_argument("output", type=Path)
    parser.add_argument("--provenance", action="store_true")
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    inputs, reports = root / "input", root / "reports"
    inputs.mkdir()
    reports.mkdir()
    reports.chmod(0o777)
    fixtures = (
        Path(__file__).resolve().parents[1]
        / "tests/fixtures"
        / {"c": "joern-argv/c", "csharp": "csharp-core", "rust": "joern-rust-env"}[args.language]
    )
    for case in ["vulnerable", "fixed"]:
        with zipfile.ZipFile(inputs / f"{case}.zip", "w") as archive:
            for file in (fixtures / case).rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(fixtures / case))
    receipts = (
        {case: fixture_receipt(inputs, case) for case in ["vulnerable", "fixed"]}
        if args.provenance
        else {}
    )
    if args.provenance:
        (inputs / "tampered.receipt.json").write_text("{}")
    image = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", args.image], text=True
    ).strip()
    results = []
    for name, bad in [("valid", False), ("mixed", True)]:
        with (inputs / "archives.csv").open("w") as target:
            writer = csv.writer(target)
            writer.writerow(
                ["repo_id", "source_type", "source_uri", "owner", "classification"]
                + (
                    ["sha256", "acquisition_receipt", "acquisition_sha256"]
                    if args.provenance
                    else []
                )
            )
            for case in ["vulnerable", "missing", "fixed"] if bad else ["vulnerable", "fixed"]:
                if case == "missing" and args.provenance:
                    writer.writerow(
                        [
                            "tampered",
                            "pvc",
                            "/input/vulnerable.zip",
                            "poc",
                            "synthetic",
                            receipts["vulnerable"][0],
                            "/input/tampered.receipt.json",
                            receipts["vulnerable"][2],
                        ]
                    )
                else:
                    writer.writerow(
                        [case, "pvc", f"/input/{case}.zip", "poc", "synthetic"]
                        + receipts.get(case, [])
                    )
        cmd = [
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
            "-e",
            f"TRACEPROOF_EXECUTION_ID={name}",
            "--entrypoint",
            "/opt/veriflow-venv/bin/python",
            image,
            "/opt/veriflow/ocp_archive_batch.py",
            "--language",
            args.language,
            "--max-rows",
            "3",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1380)
        (root / f"{name}.log").write_text(result.stdout + result.stderr)
        assert result.returncode == (1 if bad else 0), result.stdout + result.stderr
        summary = json.loads((reports / name / "batch.json").read_text())
        assert summary["state"] == ("incomplete" if bad else "exported")
        assert [i["state"] for i in summary["items"]] == (
            ["exported", "intake_not_ready", "exported"] if bad else ["exported", "exported"]
        )
        counts = []
        for item in summary["items"]:
            if item["state"] == "exported":
                report = json.loads((reports / name / item["report_path"]).read_text())
                assert report["report_id"] == item["report_id"]
                assert report["static_review_readiness"]["state"] == "incomplete"
                assert report["projection_version"] == "13"
                if args.provenance:
                    provenance = report["acquisition_provenance"]
                    assert provenance["state"] == "snapshot_bound"
                    assert provenance["resolved_commit"] == "a" * 40
                    assert provenance["archive_sha256"] == receipts[report["repo_id"]][0]
                    assert provenance["remote_history_authenticated"] is False
                else:
                    assert report["acquisition_provenance"] is None
                counts.append(report["candidate_count"])
        assert counts == [1, 0]
        results.append(
            dict(case=name, passed=True, state=summary["state"], candidate_counts=counts)
        )
    final = dict(
        passed=True,
        language=args.language,
        image_id=image,
        ocp_qualified=False,
        model_calls=0,
        synthetic_provenance=args.provenance,
        results=results,
    )
    (root / "validation.json").write_text(json.dumps(final, indent=2))
    print(json.dumps(final))


if __name__ == "__main__":
    main()
