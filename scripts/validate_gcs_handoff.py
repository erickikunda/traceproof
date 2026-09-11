"""Packaged synthetic GCS SDK-boundary handoff to a real offline language scan; no cloud calls."""

import argparse
import json
import subprocess
from pathlib import Path

from validate_acquisition_handoff import identity, runtime

FIXTURE = """
import hashlib, io, zipfile
from unittest.mock import Mock
from google.cloud.storage import Blob
from traceproof.gcs_reader import GCSReader
from traceproof.gcs_acquisition import acquire_archive
buffer = io.BytesIO()
from pathlib import Path
with zipfile.ZipFile(buffer, "w") as archive:
    for path in sorted(Path("/fixture").rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to("/fixture"))
data = buffer.getvalue()
blob = Mock(spec=Blob)
blob.generation, blob.size = 123, len(data)
blob.download_as_bytes.side_effect = lambda **kw: data[kw["start"]:kw["end"]+1]
client = Mock()
client.bucket.return_value.blob.return_value = blob
reader = GCSReader(use_adc=True, client_factory=lambda: client)
try:
    acquire_archive(reader, bucket="synthetic-bucket", name="fixture.zip", generation="123",
        expected_sha256=hashlib.sha256(data).hexdigest(), allowed_buckets=["synthetic-bucket"],
        output="/handoff/batch", repo_id="gcs-fixture", owner="poc", classification="synthetic")
finally:
    reader.close()
assert blob.reload.call_args.kwargs["if_generation_match"] == 123
assert blob.download_as_bytes.call_args.kwargs["raw_download"] is True
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--language", choices=["c", "csharp", "rust"], default="c")
    parser.add_argument("--case", choices=["vulnerable", "fixed"], default="vulnerable")
    args = parser.parse_args()
    fixture = (
        Path(__file__).resolve().parents[1]
        / "tests/fixtures"
        / {"c": "joern-argv/c", "csharp": "csharp-core", "rust": "joern-rust-env"}[args.language]
        / args.case
    )
    expected_count = 1 if args.case == "vulnerable" else 0
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    for name in ("handoff", "reports"):
        (root / name).mkdir(mode=0o777)
        (root / name).chmod(0o777)
    acquire = identity("traceproof:gcs-acquisition-linux-poc")
    scanner = identity(
        {
            "c": "traceproof:ocp-smoke-gcs-linux-poc",
            "csharp": "traceproof:ocp-smoke-gcs-csharp-linux-poc",
            "rust": "traceproof:ocp-smoke-gcs-rust-linux-poc",
        }[args.language]
    )
    for image in (acquire, scanner):
        assert image["Os"] == "linux" and image["Architecture"] == "arm64"

    def run(command, name):
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        (root / name).write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr

    run(
        runtime(
            acquire["Id"],
            [
                "--mount",
                f"type=bind,source={root / 'handoff'},target=/handoff",
                "--mount",
                f"type=bind,source={fixture},target=/fixture,readonly",
            ],
            "none",
        )
        + ["--entrypoint", "python", acquire["Id"], "-c", FIXTURE],
        "acquire.log",
    )
    mounts = [
        "--mount",
        f"type=bind,source={root / 'handoff'},target=/handoff,readonly",
        "--mount",
        f"type=bind,source={root / 'reports'},target=/reports",
    ]
    common = runtime(scanner["Id"], mounts, "none")
    run(
        common + ["--entrypoint", "python", scanner["Id"], "/opt/traceproof/runtime_probe.py"],
        "probe.json",
    )
    run(
        common
        + [
            "-e",
            "TRACEPROOF_EXECUTION_ID=gcs-scan",
            "--entrypoint",
            "python",
            scanner["Id"],
            "/opt/traceproof/ocp_archive_batch.py",
            "--input",
            "/handoff/batch",
            "--language",
            args.language,
            "--max-rows",
            "1",
        ],
        "scan.log",
    )
    batch = json.loads((root / "reports/gcs-scan/batch.json").read_text())
    assert batch["state"] == "exported"
    report_path = root / "reports/gcs-scan" / batch["items"][0]["report_path"]
    report = json.loads(report_path.read_text())
    provenance = report["acquisition_provenance"]
    assert report["projection_version"] == "14"
    assert provenance["kind"] == "gcs" and provenance["state"] == "snapshot_bound"
    assert provenance["generation"] == "123"
    assert report["candidate_count"] == expected_count
    assert report["static_review_readiness"]["state"] == "incomplete"
    result = dict(
        passed=True,
        acquisition_image=acquire["Id"],
        scanner_image=scanner["Id"],
        report_id=report["report_id"],
        candidate_count=expected_count,
        language=args.language,
        fixture_case=args.case,
        model_calls=0,
        cloud_calls=0,
        ocp_qualified=False,
        source="synthetic SDK boundary",
    )
    (root / "validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
