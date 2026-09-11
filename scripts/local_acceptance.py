"""Review retained local acceptance or explicitly rerun the bounded native fixture matrix."""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from summarize_gcs_acceptance import LANGUAGES, summarize

ROOT = Path(__file__).resolve().parents[1]
DEFERRED = [
    ("real_cloud", "Authorized GCS identity, network and real-object acceptance"),
    ("bank_git", "Bank private Git/SSO and corporate proxy acceptance"),
    ("bank_models", "Approved gateway/model behavior, accounting and data controls"),
    ("ocp_dev", "Required target-cluster SCC, registry, architecture, PVC and network acceptance"),
    ("ground_truth", "Authorized 50-repository benchmark and adjudicated quality"),
    ("fleet", "PostgreSQL concurrency/recovery and representative 1,000 repositories/day"),
]


def check_reports(matrix):
    """Recorded pass flags alone are insufficient when report artifacts are missing."""
    for row in matrix["cases"]:
        folder = Path(row["validation_path"]).parent
        batch = json.loads((folder / "reports/gcs-scan/batch.json").read_text())
        assert batch["state"] == "exported" and len(batch["items"]) == 1
        relative = Path(batch["items"][0]["report_path"])
        report_root = (folder / "reports/gcs-scan").resolve()
        report_path = (report_root / relative).resolve()
        assert report_path.is_relative_to(report_root)
        report = json.loads(report_path.read_text())
        assert report["report_id"] == row["report_id"]
        assert report["candidate_count"] == row["candidate_count"]
        assert report["projection_version"] == "14"
        provenance = report["acquisition_provenance"]
        receipt = json.loads((folder / "handoff/batch/acquisition.json").read_text())
        assert provenance["kind"] == "gcs" and provenance["state"] == "snapshot_bound"
        assert provenance["generation"] == receipt["generation"]
        assert provenance["archive_sha256"] == receipt["archive_sha256"]
        assert report["static_review_readiness"]["state"] == "incomplete"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", type=Path, help="New output folder; never overwrite prior acceptance"
    )
    parser.add_argument(
        "--run-native", action="store_true", help="Run all 18 Docker cases sequentially"
    )
    parser.add_argument("--tests", action="store_true", help="Also run the local pytest suite")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    # Resolve retained artifact paths against the checkout, independent of shell cwd.
    matrix_path = ROOT / "containers/gcs-acceptance-matrix.json"
    recorded = json.loads(matrix_path.read_text())
    results = []
    checks = []
    for name, reason in DEFERRED:
        checks.append(dict(name=name, state="deferred", reason=reason))
    if args.run_native:
        for language in LANGUAGES:
            for case in ("vulnerable", "fixed"):
                directory = output / f"{language}-{case}"
                log = output / f"{language}-{case}.log"
                with log.open("w") as target:
                    try:
                        run = subprocess.run(
                            [
                                sys.executable,
                                str(ROOT / "scripts/validate_gcs_handoff.py"),
                                str(directory),
                                "--language",
                                language,
                                "--case",
                                case,
                            ],
                            cwd=ROOT,
                            stdout=target,
                            stderr=subprocess.STDOUT,
                            timeout=900,
                        )
                        if run.returncode:
                            raise RuntimeError("Native case failed")
                        results.append(directory / "validation.json")
                    except (OSError, subprocess.TimeoutExpired, RuntimeError) as error:
                        checks.append(
                            dict(
                                name=f"{language}/{case}",
                                state="failed",
                                error_type=type(error).__name__,
                                log=str(log),
                            )
                        )
    else:
        results = [ROOT / row["validation_path"] for row in recorded["cases"]]
    try:
        matrix = summarize(results)
        check_reports(matrix)
        (output / "matrix.json").write_text(json.dumps(matrix, indent=2))
        checks.append(
            dict(
                name="gcs_language_matrix",
                state="passed",
                basis="fresh_native" if args.run_native else "retained_artifacts",
            )
        )
    except (OSError, ValueError, KeyError, AssertionError) as error:
        checks.append(
            dict(
                name="gcs_language_matrix",
                state="failed",
                error_type=type(error).__name__,
                reason="Missing or inconsistent evidence; inspect inputs or rerun native",
            )
        )
    if args.tests:
        with (output / "pytest.log").open("w") as target:
            try:
                test = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q"],
                    cwd=ROOT,
                    stdout=target,
                    stderr=subprocess.STDOUT,
                    timeout=900,
                )
                state = "passed" if test.returncode == 0 else "failed"
            except (OSError, subprocess.TimeoutExpired):
                state = "failed"
        checks.append(dict(name="application_tests", state=state))
    else:
        checks.append(
            dict(name="application_tests", state="not_run", reason="Use --tests for fresh results")
        )
    checks.append(
        dict(
            name="git_transport_and_plain_archive",
            state="not_run",
            reason="Separate existing native validators; not rerun by this command",
        )
    )
    failed = any(check["state"] == "failed" for check in checks)
    report = dict(
        schema_version="1",
        created_at=datetime.now(UTC).isoformat(),
        state="failed" if failed else "local_checks_passed_with_deferred_gates",
        mode="fresh_native" if args.run_native else "retained_evidence",
        checks=checks,
        production_ready=False,
        ocp_qualified=False,
    )
    (output / "acceptance.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
