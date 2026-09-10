"""Run the dependency-free Java smoke fixtures with an installed approved query.

Usage: uv run python scripts/validate_java.py QUERY_PATH NEW_OUTPUT_DIRECTORY
Expected query: codeql/java-queries Security/CWE/CWE-089/SqlConcatenated.ql.
No analyzed fixture code is executed and no model calls are made.
"""

import argparse
import csv
import json
import zipfile
from pathlib import Path

from traceproof.artifacts import ArtifactStore
from traceproof.intake import process, submit
from traceproof.persistence import Store, exclusive_worker
from traceproof.pipeline import scan_run
from traceproof.reports import get_report, render_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    query = args.query.resolve(strict=True)
    store = Store(root / "state")
    store.initialize()
    results = []
    try:
        for case in ["vulnerable", "fixed"]:
            archive = root / f"{case}.zip"
            source = (
                Path(__file__).resolve().parents[1] / "tests/fixtures/java" / case / "DbLookup.java"
            )
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.write(source, "DbLookup.java")
            row = dict(
                repo_id=f"java-{case}",
                source_type="pvc",
                source_uri=str(archive),
                owner="POC",
                classification="synthetic",
            )
            csv_path = root / f"{case}.csv"
            with csv_path.open("w") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            batch = submit(store, csv_path, root, case)
            with exclusive_worker(store.root):
                captured = process(store, ArtifactStore(store.root), batch)
            run = captured["items"][0]["run_id"]
            result = scan_run(store, run, query, language="java")
            if not result.get("report_id"):
                raise RuntimeError(f"{case}: no report published: {result['status']}")
            report = get_report(store, row["repo_id"], result["report_id"])
            expected = 1 if case == "vulnerable" else 0
            checks = {
                "candidate_count": report["candidate_count"] == expected,
                "query_completed": report["analysis_status"] == "completed",
                "java_scope": report["language"] == "java",
                "honest_readiness": report["static_review_readiness"]["state"] == "incomplete",
                "no_model_calls": report["triage_call_count"] == 0,
                "expected_rule": all(
                    c["rule_id"] == "java/concatenated-sql-query" for c in report["candidates"]
                ),
            }
            (root / f"{case}-report.json").write_text(render_report(report))
            (root / f"{case}-report.html").write_text(render_report(report, "html"))
            results.append(
                {"case": case, "checks": checks, "passed": all(checks.values()), "result": result}
            )
            (root / "validation.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(results[-1]), flush=True)
        if not all(case["passed"] for case in results):
            raise SystemExit(1)
    finally:
        store.close()


if __name__ == "__main__":
    main()
