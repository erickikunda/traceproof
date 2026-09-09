"""Opt-in synthetic acceptance runner. Expectations remain outside analyzed archives."""

import csv
import hashlib
import json
import time
import zipfile
from pathlib import Path

from traceproof.artifacts import ArtifactStore
from traceproof.codeql import extract
from traceproof.domain import TraceProofError
from traceproof.indexing import build_index
from traceproof.intake import process, submit
from traceproof.persistence import Store, exclusive_worker
from traceproof.reports import get_report, publish_report, render_report
from traceproof.scanning import analyze

VULNERABLE = (
    "from flask import Flask, request\napp = Flask(__name__)\n"
    '@app.route("/run")\ndef run():\n    return str(eval(request.args["expr"]))\n'
)
FIXED = VULNERABLE.replace(
    'return str(eval(request.args["expr"]))', 'return request.args.get("expr", "")'
)
FIXTURES = {
    "vulnerable": {"app.py": VULNERABLE},
    "fixed": {"app.py": FIXED},
    "incomplete": {"app.py": VULNERABLE, "broken.py": "def broken(:\n"},
}


def check_case(case, report):
    """Check workflow assertions, not benchmark precision or generalized security truth."""
    readiness = report.get("static_review_readiness", {})
    checks = {
        "not_a_clean_verdict": report.get("security_verdict") == "not_adjudicated"
        and report.get("verified_finding_count") is None
        and report.get("coverage_verified") is False,
        "no_model_calls": report.get("triage_call_count") == 0,
    }
    if case == "incomplete":
        checks.update(
            index_blocked=readiness.get("python_index_gate") == "blocked",
            review_incomplete=readiness.get("state") == "incomplete",
            analysis_not_started=report.get("analysis_status") == "not_started",
            count_unknown=report.get("candidate_count") is None,
        )
    else:
        checks.update(
            static_execution_completed=report.get("analysis_status") == "completed"
            and report.get("execution_complete") is True,
            ready_for_static_review=readiness.get("state") == "ready_for_review",
        )
        if case == "vulnerable":
            checks["seeded_candidate_found"] = report.get("candidate_count") == 1 and any(
                item["rule_id"] == "py/code-injection"
                and item["path"] == "app.py"
                and item["line"] == 5
                for item in report["candidates"]
            )
        elif case == "fixed":
            checks["seeded_candidate_absent"] = report.get("candidate_count") == 0
        else:
            raise TraceProofError("Unknown acceptance case")
    return {
        "case": case,
        "passed": all(checks.values()),
        "checks": checks,
        "report_id": report["report_id"],
        "run_id": report["run_id"],
        "snapshot_id": report["snapshot_id"],
    }


def run_acceptance(output_dir, query, timeout=300):
    query = Path(query).resolve(strict=True)
    if not query.is_file() or query.suffix != ".ql":
        raise TraceProofError("Acceptance requires the approved local CodeInjection.ql entry")
    if not 1 <= timeout <= 3600:
        raise TraceProofError("Acceptance stage timeout must be 1–3600 seconds")
    with query.open("rb") as handle:
        query_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    root = Path(output_dir).resolve()
    if root.exists():
        raise TraceProofError(
            "Acceptance output directory must be new; existing results are preserved"
        )
    root.mkdir(parents=True, mode=0o700)
    inputs = root / "inputs"
    inputs.mkdir()
    started = time.monotonic()
    results = []
    store = Store(root / "state")
    try:
        store.initialize()
        for case, sources in FIXTURES.items():
            archive = inputs / f"{case}.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                for path, text in sources.items():
                    handle.writestr(path, text)
            manifest = inputs / f"{case}.csv"
            spec = {
                "repo_id": f"acceptance-{case}",
                "owner": "synthetic-acceptance",
                "classification": "synthetic",
                "source_type": "pvc",
                "source_uri": str(archive),
            }
            with manifest.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(spec))
                writer.writeheader()
                writer.writerow(spec)
            import_id = submit(store, manifest, inputs, case)
            with exclusive_worker(store.root):
                admitted = process(store, ArtifactStore(store.root), import_id)
                run_id = admitted["items"][0]["run_id"]
                index = build_index(store, run_id)
                extraction = None
                if index["python_index_gate"] == "ready":
                    extraction = extract(store, run_id, timeout=timeout)
                    if extraction["status"] == "extracted":
                        analyze(store, extraction["attempt_id"], query, timeout=timeout)
            report = publish_report(store, spec["repo_id"])
            result = check_case(case, report)
            if case != "incomplete":
                result["checks"]["query_digest_matches"] = (
                    report.get("query_sha256") == query_digest
                )
                result["passed"] &= result["checks"]["query_digest_matches"]
            result["retrieval_identical"] = (
                get_report(store, spec["repo_id"], report["report_id"]) == report
            )
            result["passed"] &= result["retrieval_identical"]
            result["extraction_status"] = extraction["status"] if extraction else "not_requested"
            result["codeql_version"] = extraction.get("codeql_version") if extraction else None
            results.append(result)
            for format, suffix in [
                ("json", "json"),
                ("html", "html"),
                ("markdown", "md"),
                ("scan-csv", "scan.csv"),
                ("candidates-csv", "candidates.csv"),
            ]:
                (root / f"{case}.{suffix}").write_text(render_report(report, format))
            (root / "acceptance.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "runner_version": "1",
                        "cases": results,
                        "passed": len(results) == len(FIXTURES)
                        and all(item["passed"] for item in results),
                        "query_sha256": query_digest,
                        "elapsed_seconds": round(time.monotonic() - started, 3),
                        "scope": "synthetic Python workflow acceptance; not a benchmark",
                        "live_model_calls": 0,
                    },
                    indent=2,
                )
            )
        return json.loads((root / "acceptance.json").read_text())
    finally:
        store.close()
