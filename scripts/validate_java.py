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
from traceproof.bundles import build_bundle
from traceproof.claims import assess_evidence
from traceproof.intake import process, submit
from traceproof.models import Decision
from traceproof.persistence import Store, exclusive_worker
from traceproof.pipeline import scan_run
from traceproof.reports import get_report, render_report


def main(fixture="java"):
    spring = fixture == "spring"
    csharp = fixture.startswith("csharp")
    language = "csharp" if csharp else "java"
    filename = (
        "LookupController.cs" if csharp else "LookupController.java" if spring else "DbLookup.java"
    )
    rule = (
        "cs/sql-injection"
        if csharp
        else "java/sql-injection"
        if spring
        else "java/concatenated-sql-query"
    )
    parser = argparse.ArgumentParser(
        description=f"Run {fixture} source-only Java acceptance fixtures"
    )
    parser.add_argument("query", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--java-profile", choices=["dependency-free", "source-only"], default="dependency-free"
    )
    parser.add_argument("--project-layout", choices=["flat", "maven", "gradle"], default="flat")
    parser.add_argument("--auto-language", action="store_true")
    args = parser.parse_args()
    if args.project_layout != "flat" and args.java_profile != "source-only":
        parser.error("Project layouts require the source-only profile")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    query = args.query.resolve(strict=True)
    store = Store(root / "state")
    store.initialize()
    results = []
    try:
        for case in (
            ["vulnerable", "fixed", "lookalike", "incomplete"]
            if spring
            else ["vulnerable", "fixed"]
        ):
            archive = root / f"{case}.zip"
            source = (
                Path(__file__).resolve().parents[1] / "tests/fixtures" / fixture / case / filename
            )
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.write(
                    source,
                    filename if args.project_layout == "flat" else "src/main/java/" + filename,
                )
                if args.project_layout == "maven":
                    zipped.writestr(
                        "pom.xml",
                        "<project><modelVersion>4.0.0</modelVersion><groupId>synthetic</groupId><artifactId>fixture</artifactId><version>1</version></project>",
                    )
                elif args.project_layout == "gradle":
                    zipped.writestr(
                        "build.gradle",
                        'throw new RuntimeException("Build evaluation forbidden in this fixture")',
                    )
            row = dict(
                repo_id=f"{fixture}-{case}",
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
            result = scan_run(
                store,
                run,
                query,
                language="auto" if args.auto_language else language,
                java_profile=args.java_profile,
                allow_csharp_downloads=csharp,
            )
            if case == "incomplete":
                checks = {
                    "parse_blocked": result["status"] == "blocked"
                    and result["java_syntax_index"]["syntax_gate"] == "blocked",
                    "no_extraction": result["extraction_id"] is None,
                    "no_report": result["report_id"] is None,
                    "no_model_calls": result["model_calls"] == 0,
                }
                results.append(
                    {
                        "case": case,
                        "checks": checks,
                        "passed": all(checks.values()),
                        "result": result,
                    }
                )
                (root / "validation.json").write_text(json.dumps(results, indent=2))
                print(json.dumps(results[-1]), flush=True)
                continue
            if not result.get("report_id"):
                raise RuntimeError(f"{case}: no report published: {result['status']}")
            report = get_report(store, row["repo_id"], result["report_id"])
            expected = 1 if case == "vulnerable" else 0
            checks = {
                "candidate_count": report["candidate_count"] == expected,
                "query_completed": report["analysis_status"] == "completed",
                "language_scope": report["language"] == language,
                "language_selection": report["language_scope"]["language_selection"]
                == ("automatic" if args.auto_language else "explicit"),
                "syntax_index": report["language_scope"]["semantic_index"] == "not_qualified"
                if csharp
                else report["language_scope"]["syntax_index"]["syntax_gate"] == "ready",
                "honest_readiness": report["static_review_readiness"]["state"] == "incomplete",
                "no_model_calls": report["triage_call_count"] == 0,
                "expected_rule": all(c["rule_id"] == rule for c in report["candidates"]),
            }
            if spring:
                observations = report["language_scope"]["syntax_index"]["framework_observations"]
                checks["spring_annotations"] = observations["total"] == 3 and all(
                    item["spring_namespace_hint"] == (case != "lookalike")
                    for item in observations["items"]
                )
                if case == "vulnerable" and report["candidates"]:
                    candidate = report["candidates"][0]
                    bundle = build_bundle(store, result["attempt_id"], candidate["fingerprint"])
                    flow = [item for item in bundle["snippets"] if item.get("flow_id") is not None]
                    threads = {}
                    for item in flow:
                        threads.setdefault(item["flow_id"], []).append(item)
                    checks["retained_flow"] = bundle["status"] == "ready" and any(
                        {item["flow_step"] for item in nodes} == set(range(nodes[0]["flow_steps"]))
                        and nodes[0]["flow_steps"] >= 2
                        for nodes in threads.values()
                    )
                    checks["source_and_sink"] = any(
                        any(
                            item["flow_step"] == 0
                            and item["line"] == 12
                            and "@RequestParam" in item["text"]
                            for item in nodes
                        )
                        and any(
                            item["flow_step"] == item["flow_steps"] - 1
                            and item["line"] == 13
                            and "executeQuery" in item["text"]
                            for item in nodes
                        )
                        for nodes in threads.values()
                    )
                    (root / "vulnerable-bundle.json").write_text(json.dumps(bundle, indent=2))
                    claims = []
                    for kind, step, assessment in [
                        ("source", 0, "present"),
                        ("sink", 1, "present"),
                        ("flow", 0, "present"),
                        ("guard", 1, "unknown"),
                    ]:
                        item = next(n for n in flow if n["flow_step"] == step)
                        claims.append(
                            dict(
                                obligation=kind,
                                evidence_id=item["id"],
                                line=item["line"],
                                end_line=item["end_line"],
                                assessment=assessment,
                                quote=item["text"]
                                .splitlines()[item["line"] - item["excerpt_line"]]
                                .strip(),
                                explanation="Synthetic fixture advisory check",
                            )
                        )
                    decision = Decision(
                        verdict="needs_review",
                        rationale="Review modeled SQL flow",
                        evidence_ids=sorted({c["evidence_id"] for c in claims}),
                        counterevidence="Guard effectiveness unknown",
                        claims=claims,
                    )
                    gate = assess_evidence(bundle, decision)
                    checks["java_evidence_gate"] = (
                        gate["passed"] and not gate["reachability_proven"]
                    )
                    (root / "vulnerable-gate.json").write_text(json.dumps(gate, indent=2))
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
