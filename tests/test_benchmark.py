import copy
import hashlib
import json

import pytest
from sqlalchemy import func, select
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from traceproof.benchmark import check_benchmark
from traceproof.bundles import canonical
from traceproof.cli import app
from traceproof.domain import TraceProofError
from traceproof.persistence import Run, Snapshot, TriageCall


@pytest.fixture
def documents(tmp_path):
    manifest = {
        "schema_version": "1",
        "dataset_id": "synthetic",
        "dataset_version": "v1",
        "repositories": [
            {
                "repo_id": "repo",
                "snapshot_id": "a" * 64,
                "languages": ["python"],
                "weakness_scope": ["CWE-94"],
                "label_coverage": "known_positives_only",
            }
        ],
    }
    label = {
        "label_id": "label-1",
        "repo_id": "repo",
        "snapshot_id": "a" * 64,
        "root_cause_id": "cause-1",
        "cwe": "CWE-94",
        "path": "app.py",
        "file_sha256": "b" * 64,
        "line": 2,
        "end_line": 2,
        "symbol": "f",
        "adjudication_reference": "synthetic fixture definition",
    }
    labels = {
        "schema_version": "1",
        "dataset_id": "synthetic",
        "label_set_version": "v1",
        "manifest_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
        "labels": [label],
    }

    def write():
        path, answers = tmp_path / "manifest.json", tmp_path / "labels.json"
        path.write_text(json.dumps(manifest))
        answers.write_text(json.dumps(labels))
        return path, answers

    return manifest, labels, write


def test_contract_check_does_not_evaluate_or_echo_answers(documents):
    _, _, write = documents
    result = check_benchmark(*write())
    assert result["status"] == "valid_contract" and result["label_count"] == 1
    assert result["precision"] is None and result["recall"] is None
    assert not result["evaluation_performed"] and not result["local_alignment_checked"]
    assert "cause-1" not in json.dumps(result) and "app.py" not in json.dumps(result)
    assert check_benchmark(write()[0])["label_count"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("repo_id", "other"),
        ("snapshot_id", "c" * 64),
        ("cwe", "CWE-78"),
        ("path", "../secret"),
        ("path", "a/../app.py"),
        ("line", "2"),
        ("end_line", 1),
        ("adjudication_reference", " "),
    ],
)
def test_bad_labels_rejected_without_echoing_values(documents, field, value):
    _, labels, write = documents
    labels["labels"][0][field] = value
    with pytest.raises(TraceProofError):
        check_benchmark(*write())


def test_manifest_pin_and_duplicate_units(documents):
    manifest, labels, write = documents
    labels["manifest_sha256"] = "c" * 64
    with pytest.raises(TraceProofError, match="pinned"):
        check_benchmark(*write())
    labels["manifest_sha256"] = hashlib.sha256(canonical(manifest)).hexdigest()
    labels["labels"].append({**labels["labels"][0], "label_id": "second"})
    with pytest.raises(TraceProofError, match="Invalid"):
        check_benchmark(*write())
    labels["labels"].pop()
    manifest["repositories"].append(copy.deepcopy(manifest["repositories"][0]))
    with pytest.raises(TraceProofError, match="Invalid"):
        check_benchmark(*write())


def test_extra_fields_duplicate_json_keys_and_size_limit(documents):
    manifest, _, write = documents
    manifest["answers"] = "NEVER ECHO THIS"
    with pytest.raises(TraceProofError) as error:
        check_benchmark(*write())
    assert "NEVER ECHO THIS" not in str(error.value)
    path, _ = write()
    path.write_text('{"schema_version":"1","schema_version":"2"}')
    with pytest.raises(TraceProofError, match="Invalid"):
        check_benchmark(path)
    path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(TraceProofError, match="1 MiB"):
        check_benchmark(path)


def test_local_alignment_reads_metadata_without_creating_scans(store, scanned, documents):
    repo, run, _, _ = scanned
    manifest, labels, write = documents
    with store.transaction() as session:
        snapshot = session.get(Snapshot, session.get(Run, run).snapshot_id)
    manifest["repositories"][0].update(repo_id=repo, snapshot_id=snapshot.id)
    labels["manifest_sha256"] = hashlib.sha256(canonical(manifest)).hexdigest()
    labels["labels"][0].update(
        repo_id=repo, snapshot_id=snapshot.id, file_sha256=snapshot.manifest["files"][0]["sha256"]
    )
    result = check_benchmark(*write(), store=store)
    assert result["aligned_repositories"] == 1 and not result["issues"]
    labels["labels"][0]["file_sha256"] = "d" * 64
    result = check_benchmark(*write(), store=store)
    assert result["status"] == "alignment_incomplete"
    with store.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Run)) == 1
        assert session.scalar(select(func.count()).select_from(TriageCall)) == 0


def test_cli_and_unavailable_pins(store, documents):
    path, answers = documents[2]()
    runner = CliRunner()
    base = ["--state-dir", str(store.root), "benchmark-check", str(path), "--labels", str(answers)]
    assert runner.invoke(app, base).exit_code == 0
    result = runner.invoke(app, [*base, "--check-local-snapshots"])
    assert result.exit_code == 1 and "snapshot_missing" in result.output
    schema = runner.invoke(app, ["benchmark-schema"])
    assert schema.exit_code == 0 and "manifest_sha256" in schema.output
