import json
from unittest.mock import patch

import pytest
from test_ocp_smoke import ROOT, load, renderer, smoke

with patch.dict("sys.modules", {"ocp_smoke": smoke}):
    batch = load(ROOT / "containers/ocp_archive_batch.py")


def setup(tmp_path, monkeypatch, states):
    for name in ("input", "work", "reports"):
        (tmp_path / name).mkdir()
    (tmp_path / "input/archives.csv").write_text(
        "repo_id,source_type\n" + "".join(f"repo{i},pvc\n" for i in range(len(states)))
    )
    monkeypatch.setattr(batch, "submit", lambda *a: "batch")
    monkeypatch.setattr(
        batch,
        "process",
        lambda *a: {"items": [{"state": s, "run_id": str(i)} for i, s in enumerate(states)]},
    )
    return (tmp_path / "input", tmp_path / "work", tmp_path / "reports", "test", "c")


def test_continues_after_intake_rejection(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch, ["snapshotted", "rejected", "snapshotted"])
    calls = []

    def scan(*a, **k):
        calls.append(k["offset"])
        assert k["limit"] == 1 and "advisory" not in k
        return {"items": [{"status": "incomplete", "report_id": str(k["offset"])}]}

    monkeypatch.setattr(batch, "scan_import", scan)
    monkeypatch.setattr(
        batch,
        "get_report",
        lambda *a, **k: {
            "repo_id": a[1],
            "report_id": k["report_id"],
            "analysis_status": "partial",
            "candidate_count": 0,
        },
    )
    monkeypatch.setattr(batch, "render_report", lambda r, f: json.dumps(r))
    result = batch.run(*args)
    assert calls == [0, 2]
    assert result["state"] == "incomplete"
    assert [i["state"] for i in result["items"]] == ["exported", "intake_not_ready", "exported"]
    assert len(list((tmp_path / "reports/test").glob("row-*/report.json"))) == 2


def test_infrastructure_stop_keeps_pending_rows(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch, ["snapshotted", "snapshotted"])

    def fail(*a, **k):
        raise OSError("storage unavailable")

    monkeypatch.setattr(batch, "scan_import", fail)
    with pytest.raises(OSError):
        batch.run(*args)
    result = json.loads((tmp_path / "reports/test/batch.json").read_text())
    assert result["state"] == "failed"
    assert [i["state"] for i in result["items"]] == ["scanning", "pending"]
    assert "storage unavailable" not in json.dumps(result)


def test_excess_rows_reject_before_state(tmp_path, monkeypatch):
    args = setup(tmp_path, monkeypatch, ["snapshotted"] * 2)
    with pytest.raises(ValueError):
        batch.run(*args, max_rows=1)
    assert not list((tmp_path / "work").iterdir())


def test_batch_job_deadline_and_entrypoint():
    value = renderer.bundle(
        "test", "batch", "registry/image@sha256:" + "a" * 64, "input", "reports", "c", 3
    )
    job = value["items"][2]["spec"]
    assert job["activeDeadlineSeconds"] == 1380
    container = job["template"]["spec"]["containers"][0]
    assert container["command"][-1].endswith("ocp_archive_batch.py")
    assert container["args"] == ["--language", "c", "--max-rows", "3"]
    with pytest.raises(ValueError):
        renderer.bundle(
            "test", "batch", "registry/image@sha256:" + "a" * 64, "input", "reports", "c", 11
        )
