"""Native C# discovery and explicit replay advisory; never invokes a live provider."""

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
from traceproof.joern_claims import CSHARP_POLICY, assess_review_evidence
from traceproof.models import Decision, ModelConfig, ReplayAdapter, Reply, Usage
from traceproof.persistence import Store
from traceproof.pipeline import scan_run
from traceproof.reports import get_report, publish_report, render_report
from traceproof.scan_advisory import AdvisoryOptions
from traceproof.scanning import scan_report
from traceproof.triage import set_budget, triage_report


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
parser.add_argument("--repair-dir", type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=False)
fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures"
store = Store(root / "state")
store.initialize()
results = []
try:
    for name, (fixture, count, eligible) in {
        "core-vulnerable": ("csharp-core/vulnerable", 1, True),
        "core-fixed": ("csharp-core/fixed", 0, False),
        "mvc-vulnerable": ("csharp-mvc/vulnerable", 1, True),
        "mvc-fixed": ("csharp-mvc/fixed", 0, False),
        "webapi-vulnerable": ("csharp-webapi/vulnerable", 1, True),
        "webapi-fixed": ("csharp-webapi/fixed", 0, False),
        "crossfile-vulnerable": ("joern-csharp-crossfile/vulnerable", 1, True),
        "crossfile-fixed": ("joern-csharp-crossfile/fixed", 0, False),
        "foreign-source": ("joern-csharp-advisory/foreign-source", 1, False),
        "unbound-source": ("joern-csharp-advisory/unbound-source", 1, False),
    }.items():
        archive = root / f"{name}.zip"
        with zipfile.ZipFile(archive, "w") as out:
            for file in (fixtures / fixture).rglob("*.cs"):
                out.write(file, file.relative_to(fixtures / fixture))
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
            joern_repair_dir=args.repair_dir,
        )
        batch_result = scan_import(store, batch, **options)
        attempt = batch_result["items"][0]
        assert attempt["status"] == "incomplete" and attempt["report_id"]
        assert attempt["language"] == "csharp" and attempt["model_calls"] == 0
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
        for candidate in fetched["candidates"]:
            bundle = build_bundle(store, attempt["attempt_id"], candidate["fingerprint"])
            gate = assess_review_evidence(bundle, review_decision(bundle), CSHARP_POLICY)
            (root / f"{name}-gate.json").write_text(json.dumps(gate, indent=2))
            (root / f"{name}-bundle.json").write_text(json.dumps(bundle, indent=2))
            (root / f"{name}-native.json").write_text(json.dumps(native, indent=2))
            assert gate["passed"] == eligible, gate
            reply = root / f"{name}-replay.json"
            reply.write_text(
                Reply(
                    status="completed",
                    decision=review_decision(bundle),
                    usage=Usage(input_tokens=100, output_tokens=20),
                ).model_dump_json()
            )
            set_budget(store, run, 100000, max_requests=2)
            config = ModelConfig(
                provider="replay",
                model="synthetic-csharp-workflow",
                input_micro_usd_per_1k=1000,
                output_micro_usd_per_1k=2000,
            )
            advisory = AdvisoryOptions(config, ReplayAdapter(reply), "csharp-review", CSHARP_POLICY)
            reviewed = scan_run(store, run, **options, advisory=advisory)
            assert reviewed["model_calls"] == int(eligible) and reviewed["live_model_calls"] == 0, (
                reviewed
            )
            final = get_report(store, name, report_id=reviewed["report_id"])
            history = final["candidates"][0]["triage_history"][-1]
            assert (
                history["disposition"] == ("needs_review" if eligible else "abstain")
                and history["simulated"]
            ), history
            assert history["review_policy"] == CSHARP_POLICY
            assert final["static_review_readiness"]["state"] == "incomplete"
            retry = scan_import(store, batch, **options, advisory=advisory)
            assert retry["model_calls"] == 0
            ledger = triage_report(store, run)
            assert ledger["total"] == 1 and ledger["accounted_micro_usd"] == (
                140 if eligible else 0
            )
            (root / f"{name}-advisory.json").write_text(json.dumps(ledger, indent=2))
            (root / f"{name}.html").write_text(render_report(final, "html"))
            assert bundle_engine(bundle) == "joern"
            assert not requirements(bundle["rule_id"], bundle_engine(bundle))["supported"]
        results.append(dict(name=name, passed=True, candidates=count, eligible=eligible))
        (root / "case-results.json").write_text(json.dumps(results, indent=2))
finally:
    store.close()
print(results)
