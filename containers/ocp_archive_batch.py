"""Bounded sequential PVC archive batch; disposable state, no model calls."""

import argparse
import csv
import io
import json
import os
import re
from pathlib import Path

from ocp_smoke import PROFILES, archive_manifest

from veriflow.artifacts import ArtifactStore, open_scoped_source
from veriflow.batch_scan import scan_import
from veriflow.intake import process, submit
from veriflow.persistence import Store
from veriflow.reports import get_report, render_report


def checkpoint(output, summary):
    temporary = output / "batch.json.tmp"
    temporary.write_text(json.dumps(summary, indent=2))
    temporary.replace(output / "batch.json")


def run(input_root, work_root, reports_root, execution_id, language, max_rows=10):
    if language not in PROFILES or not 1 <= max_rows <= 10:
        raise ValueError("Unsupported language or batch limit")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,79}", execution_id):
        raise ValueError("Invalid execution ID")
    output = reports_root / execution_id
    output.mkdir()
    summary = dict(
        schema_version="1",
        state="failed",
        execution_id=execution_id,
        language=language,
        discovery_profile=PROFILES[language],
        items=[],
        model_calls=0,
        state_disposable=True,
        ocp_qualified=False,
    )
    store = None
    try:
        manifest = archive_manifest(input_root)
        summary["manifest_name"] = manifest.name
        with open_scoped_source(str(manifest.absolute()), input_root) as source:
            raw = source.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Manifest too large")
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True))
        if not 1 <= len(rows) <= max_rows:
            raise ValueError("Batch row limit exceeded or empty manifest")
        summary["items"] = [
            dict(row_number=i + 2, state="pending", report_id=None) for i in range(len(rows))
        ]
        summary["state"] = "running"
        checkpoint(output, summary)
        root = work_root / execution_id
        root.mkdir()
        store = Store(root / "state")
        store.initialize()
        batch_id = submit(store, manifest, input_root, execution_id)
        summary["import_id"] = batch_id
        intake = process(store, ArtifactStore(store.root), batch_id)
        if len(intake["items"]) != len(rows):
            raise ValueError("Intake row count mismatch")
        options = dict(
            engine="joern",
            language=language,
            joern_home=Path("/opt/joern-cli"),
            joern_profile=None if PROFILES[language] == "default" else PROFILES[language],
            extraction_timeout=180,
            query_timeout=180,
        )
        if language == "csharp":
            options["joern_repair_dir"] = Path("/opt/veriflow/csharp-repair")
        if language == "rust":
            options["rust_home"] = Path("/opt/rust")
        for index, item in enumerate(intake["items"]):
            entry = summary["items"][index]
            entry.update(intake_state=item["state"], run_id=item.get("run_id"))
            if item["state"] != "snapshotted" or not item.get("run_id"):
                entry["state"] = "intake_not_ready"
                checkpoint(output, summary)
                continue
            entry["state"] = "scanning"
            checkpoint(output, summary)
            result = scan_import(store, batch_id, offset=index, limit=1, **options)
            if len(result["items"]) != 1:
                entry["state"] = "not_dispatched"
            else:
                scanned = result["items"][0]
                entry.update(
                    state="scan_failed",
                    scan_status=scanned["status"],
                    report_id=scanned.get("report_id"),
                )
                if scanned.get("report_id"):
                    report = get_report(
                        store, rows[index]["repo_id"], report_id=scanned["report_id"]
                    )
                    directory = output / f"row-{index + 2:06d}"
                    directory.mkdir()
                    for fmt in ("json", "html"):
                        (directory / f"report.{fmt}").write_text(render_report(report, fmt))
                    entry.update(
                        repo_id=report["repo_id"],
                        candidate_count=report["candidate_count"],
                        report_path=f"{directory.name}/report.json",
                        analysis_status=report["analysis_status"],
                    )
                    if report["analysis_status"] == "partial":
                        entry["state"] = "exported"
            checkpoint(output, summary)
        summary["state"] = (
            "exported" if all(i["state"] == "exported" for i in summary["items"]) else "incomplete"
        )
        return summary
    except Exception as exc:
        summary.update(state="failed", error_type=type(exc).__name__)
        raise
    finally:
        if store:
            store.close()
        checkpoint(output, summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("/input"))
    parser.add_argument("--work", type=Path, default=Path("/work"))
    parser.add_argument("--reports", type=Path, default=Path("/reports"))
    parser.add_argument("--execution-id", default=os.environ.get("TRACEPROOF_EXECUTION_ID", ""))
    parser.add_argument("--language", choices=sorted(PROFILES), required=True)
    parser.add_argument("--max-rows", type=int, default=10)
    args = parser.parse_args()
    try:
        result = run(
            args.input, args.work, args.reports, args.execution_id, args.language, args.max_rows
        )
    except Exception as exc:
        print(json.dumps(dict(state="failed", error_type=type(exc).__name__)))
        return 1
    print(json.dumps(result))
    return 0 if result["state"] == "exported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
