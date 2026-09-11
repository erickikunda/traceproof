"""Restricted native CWE-89 fixture acceptance; no model calls."""

import csv
import json
import zipfile
from pathlib import Path

from traceproof.artifacts import ArtifactStore
from traceproof.intake import process, submit
from traceproof.persistence import Store
from traceproof.pipeline import scan_run
from traceproof.reports import get_report, render_report

root = Path("/work/csharp-query-validation")
root.mkdir()
fixtures = Path("/repo/tests/fixtures/joern-csharp-query")
results = []
store = Store(root / "state")
try:
    store.initialize()
    for case, count in {
        "vulnerable": 1,
        "fixed": 0,
        "crossfile": 1,
        "disconnected": 0,
        "foreign-source": 0,
        "unbound-source": 0,
        "guard-unknown": 1,
    }.items():
        archive = root / f"{case}.zip"
        with zipfile.ZipFile(archive, "w") as target:
            for path in (fixtures / case).glob("*.cs"):
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
            language="csharp",
            joern_home=Path("/opt/joern-cli"),
            joern_profile="csharp-query-commandtext-v1",
            joern_repair_dir=Path("/opt/traceproof/csharp-repair"),
        )
        report = get_report(store, case, report_id=result["report_id"])
        assert report["candidate_count"] == count, (case, report)
        assert result["model_calls"] == 0
        for format in ("html", "json", "scan-csv"):
            rendered = render_report(report, format)
            if count:
                assert "CWE-89" in rendered
        Path(f"/reports/{case}.html").write_text(render_report(report, "html"))
        results.append(dict(case=case, candidates=count, report_id=result["report_id"]))
finally:
    store.close()
Path("/reports/validation.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results))
