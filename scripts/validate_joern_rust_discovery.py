"""Opt-in durable experimental Rust discovery fixture pair; no LLM calls."""

import argparse
import csv
import json
import zipfile
from pathlib import Path

from veriflow.artifacts import ArtifactStore
from veriflow.bundles import build_bundle
from veriflow.claims import bundle_engine, requirements
from veriflow.intake import process, submit
from veriflow.joern import discover
from veriflow.persistence import Store
from veriflow.reports import publish_report, render_report
from veriflow.scanning import scan_report

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--joern-home", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--rust-home", type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
root.mkdir(parents=True, exist_ok=False)
fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/joern-rust"
store = Store(root / "state")
store.initialize()
results = []
try:
    for name, count in {
        "vulnerable": 1,
        "fixed": 0,
        "crossfile-vulnerable": 1,
        "crossfile-fixed": 0,
        "disconnected": 0,
    }.items():
        archive = root / f"{name}.zip"
        with zipfile.ZipFile(archive, "w") as out:
            for file in (fixtures / name).rglob("*"):
                if file.is_file():
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
        attempt = discover(store, run, args.joern_home, language="rust", rust_home=args.rust_home)
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
            for node in flow:
                path = Path(node["file"])
                if not path.is_absolute():
                    path = scan_root / "source" / path
                assert path.resolve().is_relative_to(scan_root / "source")
                assert node["code"] in path.read_text().splitlines()[node["line"] - 1]
        for candidate in fetched["candidates"]:
            bundle = build_bundle(store, attempt["attempt_id"], candidate["fingerprint"])
            assert bundle_engine(bundle) == "joern"
            assert not requirements(bundle["rule_id"], bundle_engine(bundle))["supported"]
        results.append(dict(name=name, passed=True, candidates=count))
        (root / "case-results.json").write_text(json.dumps(results, indent=2))
finally:
    store.close()
print(results)
