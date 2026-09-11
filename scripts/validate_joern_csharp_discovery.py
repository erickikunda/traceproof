"""Opt-in durable experimental C# discovery fixture pair; no LLM calls."""

import argparse
import csv
import json
import zipfile
from pathlib import Path

from traceproof.artifacts import ArtifactStore
from traceproof.bundles import build_bundle
from traceproof.claims import bundle_engine, requirements
from traceproof.intake import process, submit
from traceproof.joern import discover
from traceproof.persistence import Store
from traceproof.reports import publish_report, render_report
from traceproof.scanning import scan_report

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--joern-home", type=Path, required=True)
parser.add_argument("--repair-dir", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=False)
fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/joern-csharp-crossfile"
store = Store(root / "state")
store.initialize()
results = []
try:
    for name, count in {"vulnerable": 1, "fixed": 0}.items():
        archive = root / f"{name}.zip"
        with zipfile.ZipFile(archive, "w") as out:
            for file in (fixtures / name).glob("*.cs"):
                out.write(file, file.name)
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
        attempt = discover(store, run, args.joern_home, repair_dir=args.repair_dir)
        fetched = scan_report(store, name, run, attempt["attempt_id"])
        published = publish_report(store, name, run, attempt["attempt_id"])
        (root / f"{name}.html").write_text(render_report(published, "html"))
        (root / f"{name}.json").write_text(json.dumps(fetched, indent=2))
        assert fetched["status"] == "partial", fetched
        assert fetched["candidate_count"] == count, fetched
        assert fetched["execution_complete"] is False
        assert published["static_review_readiness"]["state"] == "incomplete"
        assert published["source_mapping"]["validated_paths"] == count
        assert published["source_mapping"]["unsupported_paths"] == 0
        for candidate in fetched["candidates"]:
            bundle = build_bundle(store, attempt["attempt_id"], candidate["fingerprint"])
            assert bundle_engine(bundle) == "joern"
            assert not requirements(bundle["rule_id"], bundle_engine(bundle))["supported"]
        results.append(dict(name=name, passed=True, candidates=count))
        (root / "case-results.json").write_text(json.dumps(results, indent=2))
finally:
    store.close()
print(results)
