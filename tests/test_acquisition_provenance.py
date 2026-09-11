import csv
import hashlib
import json

import pytest
from test_git_acquisition import run
from test_git_acquisition import source_repo as source_repo

from traceproof.artifacts import ArtifactStore
from traceproof.intake import process, submit
from traceproof.reports import get_report, publish_report, render_report


def rewrite_csv(path, updates):
    with path.open() as source:
        rows = list(csv.DictReader(source))
    rows[0].update(updates)
    with path.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_receipt_survives_source_sidecar_removal(tmp_path, source_repo, store):
    output = tmp_path / "acquired"
    receipt = run(output)
    imported = submit(store, output / "input.csv", output, "receipt")
    (output / "acquisition.json").unlink()
    assert submit(store, output / "input.csv", output, "receipt") == imported
    result = process(store, ArtifactStore(store.root), imported)
    assert result["items"][0]["state"] == "snapshotted"
    report = publish_report(store, "example", result["items"][0]["run_id"])
    provenance = report["acquisition_provenance"]
    assert provenance["resolved_commit"] == receipt["resolved_commit"]
    assert provenance["state"] == "snapshot_bound"
    assert provenance["remote_history_authenticated"] is False
    assert get_report(store, "example", report_id=report["report_id"]) == report
    assert receipt["resolved_commit"] in render_report(report, "html")
    assert receipt["resolved_commit"] in render_report(report, "scan-csv")


@pytest.mark.parametrize("change", ["digest", "repo", "archive", "inventory"])
def test_receipt_mismatch_is_not_bound(tmp_path, source_repo, store, change):
    output = tmp_path / "acquired"
    run(output)
    path = output / "acquisition.json"
    receipt = json.loads(path.read_text())
    if change == "repo":
        receipt["repo_id"] = "other"
    if change == "archive":
        receipt["archive_sha256"] = "a" * 64
    if change == "inventory":
        receipt["files"][0]["sha256"] = "b" * 64
    path.write_text(json.dumps(receipt) + "\n")
    if change != "digest":
        rewrite_csv(
            output / "input.csv",
            {"acquisition_sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
        )
    imported = submit(store, output / "input.csv", output, "receipt")
    result = process(store, ArtifactStore(store.root), imported)
    item = result["items"][0]
    assert item["state"] == ("failed" if change == "inventory" else "rejected")
    if item["run_id"]:
        report = publish_report(store, "example", item["run_id"])
        assert report["acquisition_provenance"]["state"] == "admitted"
        assert report["snapshot_id"] is None
