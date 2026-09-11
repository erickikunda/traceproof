"""Evaluate retained synthetic Rust results without rerunning scans or models."""

import argparse
import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from traceproof.bundles import canonical
from traceproof.evaluation import render_scorecard
from traceproof.persistence import Run, ScanAttempt, Snapshot, Store
from traceproof.reports import publish_report
from traceproof.scorecards import get_scorecard, publish_scorecard

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
store = Store(args.state)
try:
    with store.transaction() as session:
        run = session.scalar(select(Run).where(Run.repo_id == "vulnerable"))
        attempt = session.scalar(select(ScanAttempt).where(ScanAttempt.run_id == run.id))
        snapshot = session.get(Snapshot, run.snapshot_id)
        file_hash = next(f["sha256"] for f in snapshot.manifest["files"] if f["path"] == "main.rs")
        run_id, attempt_id, snapshot_id = run.id, attempt.id, snapshot.id
    report = publish_report(store, "vulnerable", run_id, attempt_id)
    assert report["scanner"]["engine_id"] == "joern" and report["language"] == "rust"
    manifest = dict(
        schema_version="1",
        dataset_id="synthetic-rust-audit",
        dataset_version="v1",
        repositories=[
            dict(
                repo_id="vulnerable",
                snapshot_id=snapshot_id,
                languages=["rust"],
                weakness_scope=["CWE-78"],
                label_coverage="known_positives_only",
            )
        ],
    )
    digest = hashlib.sha256(canonical(manifest)).hexdigest()
    labels = dict(
        schema_version="1",
        dataset_id=manifest["dataset_id"],
        label_set_version="v1",
        manifest_sha256=digest,
        labels=[
            dict(
                label_id="shell-input",
                repo_id="vulnerable",
                snapshot_id=snapshot_id,
                root_cause_id="shell-input",
                cwe="CWE-78",
                path="main.rs",
                file_sha256=file_hash,
                line=3,
                end_line=3,
                symbol="lookup",
                adjudication_reference="Synthetic vulnerable fixture; independent expected sink",
            )
        ],
    )
    plan = dict(
        schema_version="2",
        mode="discovery_coverage_audit",
        engine="joern",
        manifest_sha256=digest,
        query_sha256=report["query_sha256"],
        scanner_version=report["scanner"]["version"],
        profile="standard",
        rule_ids=["traceproof/joern-rust-lookup-arg-v1"],
        reports=[dict(repo_id="vulnerable", report_id=report["report_id"])],
    )
    paths = []
    for name, value in [("manifest", manifest), ("labels", labels), ("plan", plan)]:
        path = args.output / f"{name}.json"
        path.write_text(json.dumps(value, indent=2))
        paths.append(path)
    result = publish_scorecard(store, *paths)
    assert result == get_scorecard(store, manifest["dataset_id"], result["scorecard_id"])
    assert result["label_counts"]["not_evaluable"] == 1
    assert result["candidate_recall_proxy"]["value"] is None
    assert result["repositories"][0]["candidate_count"] == 1
    assert result["repositories"][0]["scope_gaps"] == [
        "discovery_profile_not_qualified_for_recall",
        "analysis_incomplete",
    ]
    for format in ["json", "html", "markdown", "repositories-csv", "summary-csv"]:
        (args.output / f"audit.{format}").write_text(render_scorecard(result, format))
    print(json.dumps({"passed": True, "scorecard_id": result["scorecard_id"], "model_calls": 0}))
finally:
    store.close()
