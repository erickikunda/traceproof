"""Restricted native automatic profile acceptance; no model calls."""

import csv
import json
import zipfile
from pathlib import Path

from traceproof.artifacts import ArtifactStore
from traceproof.intake import process, submit
from traceproof.persistence import Store
from traceproof.pipeline import scan_run
from traceproof.reports import get_report

root = Path("/work/auto-validation")
root.mkdir()
fixtures = Path("/repo/tests/fixtures/joern-flask-sql")
results = []
store = Store(root / "state")
try:
    store.initialize()
    for case, _count in {"vulnerable": 1}.items():
        archive = root / f"{case}.zip"
        with zipfile.ZipFile(archive, "w") as target:
            for path in (fixtures / case).glob("*.py"):
                target.write(path, path.name)
        manifest = root / f"{case}.csv"
        with manifest.open("w") as target:
            row = dict(
                repo_id=case,
                source_type="pvc",
                source_uri=str(archive),
                owner="poc",
                classification="synthetic",
            )
            writer = csv.DictWriter(target, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        imported = submit(store, manifest, root, case)
        run = process(store, ArtifactStore(store.root), imported)["items"][0]["run_id"]
        result = scan_run(
            store,
            run,
            engine="joern",
            language="auto",
            joern_home=Path("/opt/joern-cli"),
            joern_profile="auto",
        )
        assert len(result["report_ids"]) == 4, result
        assert result["model_calls"] == 0
        counts = {}
        for item in result["items"]:
            report = get_report(store, case, report_id=item["report_id"])
            counts[item["discovery_profile"]] = report["candidate_count"]
        assert counts["python-flask-sql-v1"] == 1, counts
        assert sum(counts.values()) == 1, counts
        retry = scan_run(
            store,
            run,
            engine="joern",
            language="auto",
            joern_home=Path("/opt/joern-cli"),
            joern_profile="auto",
            skip_existing=True,
        )
        assert all(item["status"] == "skipped_existing_attempt" for item in retry["items"]), retry
        results.append(dict(counts=counts, selection=result, retry=retry))
finally:
    store.close()
Path("/reports/validation.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results))
