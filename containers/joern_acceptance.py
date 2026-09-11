"""Durable synthetic acceptance inside the externally restricted Joern image."""

import csv
import json
import shutil
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

root = Path("/work/acceptance")
root.mkdir()
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
        "malformed": 0,
        "partial-parse": 1,
    }.items():
        archive = root / f"{name}.zip"
        with zipfile.ZipFile(archive, "w") as out:
            for file in (Path("/opt/traceproof/fixtures") / name).glob("*.java"):
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
        attempt = discover(store, run, "/opt/joern-cli")
        fetched = scan_report(store, name, run, attempt["attempt_id"])
        published = publish_report(store, name, run, attempt["attempt_id"])
        Path(f"/reports/{name}.html").write_text(render_report(published, "html"))
        Path(f"/reports/{name}.json").write_text(json.dumps(fetched, indent=2))
        assert fetched["status"] == "partial", fetched
        assert fetched["candidate_count"] == count, fetched
        assert fetched["execution_complete"] is False
        assert fetched["diagnostic_errors"] is None
        assert fetched["discovery_coverage"]["represented_java_files"] == (
            0 if name == "malformed" else 3
        )
        if name in {"malformed", "partial-parse"}:
            assert (
                "Broken.java"
                in fetched["joern_diagnostics"]["stages"]["prepare"]["parser_problem_files"]
            )
            assert "Broken.java" in fetched["discovery_coverage"]["missing_graph_files"]
        assert published["static_review_readiness"]["state"] == "incomplete"
        for candidate in fetched["candidates"]:
            bundle = build_bundle(store, attempt["attempt_id"], candidate["fingerprint"])
            assert bundle_engine(bundle) == "joern"
            assert not requirements(bundle["rule_id"], bundle_engine(bundle))["supported"]
        results.append(
            dict(name=name, passed=True, candidates=count, coverage=fetched["discovery_coverage"])
        )
        Path("/reports/case-results.json").write_text(json.dumps(results, indent=2))
finally:
    for file in root.rglob("*.log"):
        target = Path("/reports/diagnostics") / file.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
    store.close()
