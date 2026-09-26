import hashlib
import io
import json
import zipfile

import pytest
from test_acquisition_provenance import rewrite_csv
from test_gcs_acquisition import Reader, execute

from veriflow.artifacts import ArtifactStore
from veriflow.intake import process, submit
from veriflow.reports import get_report, publish_report, render_report


def handoff(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("app.py", 'print("fixture")')
    execute(tmp_path, Reader(buffer.getvalue()))
    return tmp_path / "out"


def test_gcs_report_survives_receipt_removal(tmp_path, store):
    output = handoff(tmp_path)
    imported = submit(store, output / "archives.csv", output, "gcs")
    (output / "acquisition.json").unlink()
    result = process(store, ArtifactStore(store.root), imported)
    item = result["items"][0]
    assert item["state"] == "snapshotted"
    report = publish_report(store, "fixture", item["run_id"])
    provenance = report["acquisition_provenance"]
    assert provenance["state"] == "snapshot_bound"
    assert provenance["kind"] == "gcs" and provenance["generation"] == "123"
    assert "resolved_commit" not in provenance
    assert provenance["remote_history_authenticated"] is False
    assert get_report(store, "fixture", report_id=report["report_id"]) == report
    for format in ("html", "markdown", "scan-csv"):
        assert "approved-bucket" in render_report(report, format)


@pytest.mark.parametrize("change", ["digest", "repo_id", "size"])
def test_gcs_binding_failure(tmp_path, store, change):
    output = handoff(tmp_path)
    path = output / "acquisition.json"
    receipt = json.loads(path.read_text())
    if change == "repo_id":
        receipt["repo_id"] = "different"
    elif change == "size":
        receipt["size"] += 1
    path.write_text(json.dumps(receipt) + "\n")
    if change != "digest":
        rewrite_csv(
            output / "archives.csv",
            {"acquisition_sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
        )
    imported = submit(store, output / "archives.csv", output, "gcs")
    item = process(store, ArtifactStore(store.root), imported)["items"][0]
    assert item["state"] == ("failed" if change == "size" else "rejected")
