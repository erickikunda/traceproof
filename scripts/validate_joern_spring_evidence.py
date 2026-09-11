"""Validate bounded Joern Spring native-evidence discovery through the main pipeline."""

import argparse
import csv
import json
import zipfile
from pathlib import Path

from traceproof.artifacts import ArtifactStore
from traceproof.batch_scan import scan_import
from traceproof.bundles import build_bundle
from traceproof.claims import bundle_engine, requirements
from traceproof.intake import process, submit
from traceproof.joern_claims import assess_spring_evidence
from traceproof.models import Decision
from traceproof.persistence import Store
from traceproof.pipeline import scan_run
from traceproof.reports import publish_report, render_report
from traceproof.scanning import scan_report


def review_decision(bundle):
    """Deterministic fixture claims, not generated analysis or a provider response."""
    nodes = [s for s in bundle["snippets"] if s.get("flow_id") == "F0T0"]
    first, last = nodes[0], nodes[-1]
    claims = []
    for kind, node, assessment in [
        ("source", first, "present"),
        ("sink", last, "present"),
        ("flow", first, "present"),
        ("guard", last, "unknown"),
    ]:
        claims.append(
            dict(
                obligation=kind,
                evidence_id=node["id"],
                line=node["line"],
                end_line=node["line"],
                assessment=assessment,
                quote=node["text"].splitlines()[node["line"] - node["excerpt_line"]].strip(),
                explanation="Synthetic source-bound review claim",
            )
        )
    return Decision(
        verdict="needs_review",
        rationale="Review recorded candidate",
        evidence_ids=[first["id"], last["id"]],
        counterevidence="Guards unknown",
        claims=claims,
    )


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--joern-home", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=False)
fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/joern-java"
store = Store(root / "state")
store.initialize()
results = []
try:
    for name, count in {
        "vulnerable": 1,
        "fixed": 0,
        "disconnected": 0,
        "renamed": 1,
        "annotation-lookalike": 0,
        "sink-lookalike": 0,
        "unmapped-route": 0,
    }.items():
        archive = root / f"{name}.zip"
        with zipfile.ZipFile(archive, "w") as out:
            for file in (fixtures / name).rglob("*"):
                if not file.is_file():
                    continue
                out.write(file, file.relative_to(fixtures / name))
        row = dict(
            repo_id=name,
            source_type="pvc",
            source_uri=str(archive),
            owner="poc",
            classification="synthetic",
        )
        manifest = root / f"{name}.csv"
        with manifest.open("w") as out:
            writer = csv.DictWriter(out, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        batch = submit(store, manifest, root, name)
        run = process(store, ArtifactStore(store.root), batch)["items"][0]["run_id"]
        options = dict(
            engine="joern",
            language="auto",
            joern_home=args.joern_home,
        )
        batch_result = scan_import(store, batch, **options)
        attempt = batch_result["items"][0]
        assert attempt["status"] == "incomplete" and attempt["report_id"]
        assert attempt["language"] == "java" and attempt["model_calls"] == 0
        retried = scan_import(store, batch, **options)["items"][0]
        assert retried["status"] == "skipped_existing_attempt"
        assert retried["attempt_id"] == attempt["attempt_id"]
        if name == "fixed":
            rescanned = scan_run(store, run, **options)
            assert rescanned["attempt_id"] != attempt["attempt_id"]
            assert rescanned["status"] == "incomplete"
        fetched = scan_report(store, name, run, attempt["attempt_id"])
        published = publish_report(store, name, run, attempt["attempt_id"])
        (root / f"{name}.html").write_text(render_report(published, "html"))
        (root / f"{name}.json").write_text(json.dumps(fetched, indent=2))
        assert fetched["status"] == "partial", fetched
        assert fetched["candidate_count"] == count, fetched
        assert fetched["execution_complete"] is False
        assert published["static_review_readiness"]["state"] == "incomplete"
        assert fetched["discovery_coverage"]["missing_graph_files"] == []
        # Fixture-level coordinate acceptance; no general source-span qualification claim.
        scan_root = store.root / "scans" / attempt["attempt_id"]
        native = json.loads((scan_root / "flows.json").read_text())
        for flow in native["paths"]:
            for node in (flow[0], flow[-1]):
                path = Path(node["file"])
                if not path.is_absolute():
                    path = scan_root / "source" / path
                assert path.resolve().is_relative_to(scan_root / "source")
                assert node["code"] in path.read_text().splitlines()[node["line"] - 1]
        for candidate in fetched["candidates"]:
            bundle = build_bundle(store, attempt["attempt_id"], candidate["fingerprint"])
            gate = assess_spring_evidence(bundle, review_decision(bundle))
            assert gate["passed"] and not gate["automatic_triage_enabled"], gate
            (root / f"{name}-gate.json").write_text(json.dumps(gate, indent=2))
            assert bundle_engine(bundle) == "joern"
            assert not requirements(bundle["rule_id"], bundle_engine(bundle))["supported"]
        results.append(dict(name=name, passed=True, candidates=count))
        (root / "case-results.json").write_text(json.dumps(results, indent=2))
finally:
    store.close()
print(results)
