"""One offline archive-to-report smoke run; disposable SQLite, no model configuration."""

import argparse
import csv
import io
import json
import os
import re
from pathlib import Path

from traceproof.artifacts import ArtifactStore, open_scoped_source
from traceproof.intake import process, submit
from traceproof.persistence import Store
from traceproof.pipeline import scan_run
from traceproof.reports import get_report, render_report

PROFILES = json.loads(Path(__file__).with_name("ocp-smoke-profiles.json").read_text())


def archive_manifest(input_root):
    """Select exactly one supported manifest; never silently choose between batches."""
    git_manifest = input_root / "repositories.csv"
    if git_manifest.exists() or git_manifest.is_symlink():
        raise ValueError("Git manifest is unsupported by the offline archive smoke Job")
    matches = [
        input_root / name
        for name in ("archives.csv", "input.csv")
        if (input_root / name).exists() or (input_root / name).is_symlink()
    ]
    if len(matches) != 1:
        raise ValueError("Supply archives.csv or legacy input.csv, but not both")
    return matches[0]


def run(input_root, work_root, reports_root, execution_id, joern_home, language="c"):
    if language not in PROFILES:
        raise ValueError("Unsupported smoke language/toolchain")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]{0,79}", execution_id):
        raise ValueError("Invalid execution ID")
    # Unique directory creation prevents retries from overwriting a previous export.
    output = reports_root / execution_id
    output.mkdir()
    summary = {
        "schema_version": "1",
        "execution_id": execution_id,
        "state": "failed",
        "ocp_qualified": False,
        "model_calls": 0,
        "state_disposable": True,
        "language": language,
        "discovery_profile": PROFILES[language],
    }
    store = None
    root = work_root / execution_id
    try:
        manifest = archive_manifest(input_root)
        summary["manifest_name"] = manifest.name
        with open_scoped_source(str(manifest.absolute()), input_root) as source:
            raw = source.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Manifest too large")
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        if len(rows) != 1 or rows[0].get("source_type") != "pvc":
            raise ValueError("Smoke input requires exactly one PVC archive")
        root.mkdir()
        store = Store(root / "state")
        store.initialize()
        batch = submit(store, manifest, input_root, execution_id)
        result = process(store, ArtifactStore(store.root), batch)
        items = result["items"]
        if len(items) != 1 or not items[0].get("run_id"):
            raise ValueError("Input admission failed")
        tool_options = {}
        if language == "csharp":
            tool_options["joern_repair_dir"] = Path("/opt/traceproof/csharp-repair")
        elif language == "rust":
            tool_options["rust_home"] = Path("/opt/rust")
        scanned = scan_run(
            store,
            items[0]["run_id"],
            engine="joern",
            language=language,
            joern_home=joern_home,
            joern_profile=None if PROFILES[language] == "default" else PROFILES[language],
            extraction_timeout=180,
            query_timeout=180,
            **tool_options,
        )
        if not scanned.get("report_id"):
            raise ValueError("No published report")
        report = get_report(store, rows[0]["repo_id"], report_id=scanned["report_id"])
        for fmt in ("json", "html"):
            (output / f"report.{fmt}").write_text(render_report(report, fmt))
        summary.update(
            state="exported",
            report_id=report["report_id"],
            run_id=items[0]["run_id"],
            scan=scanned,
            review_readiness=report["static_review_readiness"]["state"],
        )
        # A failed scan may still publish useful diagnostics; it must fail the Job.
        if scanned.get("analysis_status") != "partial":
            raise ValueError("Scan failed")
        return summary
    except Exception as exc:
        summary.update(state="failed", error_type=type(exc).__name__)
        raise
    finally:
        if store:
            store.close()
        # Bounded diagnostics survive disposable state; logs may contain source text.
        diagnostics = output / "diagnostics"
        for number, log in enumerate(sorted(root.rglob("*.log"))):
            if number >= 16:
                break
            if log.is_symlink() or not log.is_file():
                continue
            diagnostics.mkdir(exist_ok=True)
            with log.open("rb") as source:
                (diagnostics / f"{number}-{log.name}").write_bytes(source.read(1024 * 1024))
        (output / "result.json").write_text(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("/input"))
    parser.add_argument("--work", type=Path, default=Path("/work"))
    parser.add_argument("--reports", type=Path, default=Path("/reports"))
    parser.add_argument("--execution-id", default=os.environ.get("TRACEPROOF_EXECUTION_ID"))
    parser.add_argument("--joern-home", type=Path, default=Path("/opt/joern-cli"))
    parser.add_argument(
        "--language",
        choices=sorted(PROFILES),
        default="c" if "c" in PROFILES else next(iter(PROFILES)),
    )
    args = parser.parse_args()
    try:
        result = run(
            args.input,
            args.work,
            args.reports,
            args.execution_id or "",
            args.joern_home,
            args.language,
        )
    except Exception as exc:
        print(json.dumps({"state": "failed", "error_type": type(exc).__name__}), flush=True)
        return 1
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
