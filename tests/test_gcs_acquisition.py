import csv
import hashlib
import io
import json
import zipfile

import pytest

from veriflow.domain import TraceProofError
from veriflow.gcs_acquisition import ObjectVersion, acquire_archive


class Reader:
    def __init__(self, data, generation="123", size=None):
        self.data, self.generation = data, generation
        self.size = len(data) if size is None else size
        self.calls = []

    def stat(self, bucket, name, generation):
        self.calls.append((bucket, name, generation))
        return ObjectVersion(bucket, name, self.generation, self.size)

    def chunks(self, version):
        yield self.data


def execute(tmp_path, reader, **overrides):
    options = dict(
        bucket="approved-bucket",
        name="folder/source.zip",
        generation="123",
        expected_sha256=hashlib.sha256(reader.data).hexdigest(),
        allowed_buckets=["approved-bucket"],
        output=tmp_path / "out",
        repo_id="fixture",
        owner="poc",
        classification="synthetic",
    )
    return acquire_archive(reader, **(options | overrides))


def test_archive_handoff(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("app.py", 'print("fixture")')
    reader = Reader(buffer.getvalue())
    receipt = execute(tmp_path, reader)
    assert receipt["state"] == "acquired" and receipt["model_calls"] == 0
    row = next(csv.DictReader((tmp_path / "out/archives.csv").open()))
    assert row["sha256"] == hashlib.sha256(buffer.getvalue()).hexdigest()
    assert reader.calls == [("approved-bucket", "folder/source.zip", "123")]
    with pytest.raises(TraceProofError, match="already exists"):
        execute(tmp_path, reader)


@pytest.mark.parametrize(
    "generation,size,digest", [("124", None, None), ("123", 99, None), ("123", None, "0" * 64)]
)
def test_failed_download_never_publishes(tmp_path, generation, size, digest):
    reader = Reader(b"fixture", generation, size)
    with pytest.raises(TraceProofError):
        execute(tmp_path, reader, **({"expected_sha256": digest} if digest else {}))
    assert not (tmp_path / "out/archives.csv").exists()
    assert not (tmp_path / "out/source.zip").exists()
    assert json.loads((tmp_path / "out/acquisition.json").read_text())["state"] == "failed"


def test_unapproved_bucket_before_reader(tmp_path):
    reader = Reader(b"fixture")
    with pytest.raises(TraceProofError):
        execute(tmp_path, reader, allowed_buckets=[])
    assert not reader.calls and not (tmp_path / "out").exists()
