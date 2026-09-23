import hashlib
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from veriflow.cli import app
from veriflow.domain import TraceProofError
from veriflow.gcs_acquisition import acquire_archive
from veriflow.gcs_reader import GCSReader


def test_sdk_generation_ranges_and_raw_bytes(tmp_path):
    data = b"x" * (1024 * 1024 + 7)
    blob = Mock(generation=123, size=len(data))
    blob.download_as_bytes.side_effect = lambda **kw: data[kw["start"] : kw["end"] + 1]
    client = Mock()
    client.bucket.return_value.blob.return_value = blob
    reader = GCSReader(use_adc=True, client_factory=lambda: client)
    try:
        result = acquire_archive(
            reader,
            bucket="approved-bucket",
            name="a.zip",
            generation="123",
            expected_sha256=hashlib.sha256(data).hexdigest(),
            allowed_buckets=["approved-bucket"],
            output=tmp_path / "out",
            repo_id="fixture",
            owner="poc",
            classification="synthetic",
        )
    finally:
        reader.close()
    assert result["state"] == "acquired"
    client.bucket.return_value.blob.assert_called_once_with("a.zip", generation=123)
    assert blob.reload.call_args.kwargs["if_generation_match"] == 123
    assert blob.reload.call_args.kwargs["retry"] is None
    assert blob.download_as_bytes.call_count == 2
    for call in blob.download_as_bytes.call_args_list:
        assert call.kwargs["raw_download"] is True
        assert call.kwargs["if_generation_match"] == 123
        assert call.kwargs["retry"] is None
        assert 0 < call.kwargs["timeout"] <= 30
    client.close.assert_called_once()


def test_cli_requires_credential_opt_in(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "acquire-gcs",
            "approved-bucket",
            "a.zip",
            "123",
            "0" * 64,
            str(tmp_path / "out"),
            "fixture",
            "poc",
            "synthetic",
            "--allowed-bucket",
            "approved-bucket",
        ],
    )
    assert result.exit_code == 1
    assert not (tmp_path / "out").exists()


def test_sdk_failure_sanitized_and_no_manifest(tmp_path):
    client = Mock()
    client.bucket.side_effect = RuntimeError("secret-provider-details")
    reader = GCSReader(use_adc=True, client_factory=lambda: client)
    with pytest.raises(TraceProofError) as error:
        acquire_archive(
            reader,
            bucket="approved-bucket",
            name="a.zip",
            generation="123",
            expected_sha256="0" * 64,
            allowed_buckets=["approved-bucket"],
            output=tmp_path / "out",
            repo_id="fixture",
            owner="poc",
            classification="synthetic",
        )
    assert "secret-provider-details" not in str(error.value)
    assert not (tmp_path / "out/archives.csv").exists()
