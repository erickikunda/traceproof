"""Offline receipt binding; does not authenticate remote history or re-fetch Git."""

import hashlib
import json
from urllib.parse import urlsplit

from pydantic import Field, ValidationError

from veriflow.artifacts import open_scoped_source
from veriflow.domain import Contract, Digest, FileRecord, Identifier, VeriFlowError
from veriflow.git_acquisition import validate_remote


class GitFile(FileRecord):
    git_blob: str = Field(pattern=r"^[a-f0-9]{40}$")


class Receipt(Contract):
    schema_version: str = Field(pattern=r"^1$")
    state: str = Field(pattern=r"^acquired$")
    url: str = Field(max_length=4096)
    requested_revision: str = Field(max_length=220)
    repo_id: Identifier
    model_calls: int = Field(ge=0, le=0)
    coverage_verified: bool
    resolved_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    git_version: str = Field(min_length=1, max_length=200)
    archive_sha256: Digest
    files: list[GitFile] = Field(min_length=1, max_length=2000)
    source_bytes: int = Field(ge=0, le=100 * 1024 * 1024)
    omissions: list = Field(max_length=0)
    limitations: list[str] = Field(max_length=20)


class GCSReceipt(Contract):
    schema_version: str = Field(pattern=r"^1$")
    kind: str = Field(pattern=r"^gcs$")
    state: str = Field(pattern=r"^acquired$")
    repo_id: Identifier
    bucket: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$")
    object: str = Field(min_length=1, max_length=1024)
    generation: str = Field(pattern=r"^[1-9][0-9]{0,29}$")
    archive_sha256: Digest
    size: int = Field(gt=0, le=1024 * 1024 * 1024)
    model_calls: int = Field(ge=0, le=0)
    scans_started: int = Field(ge=0, le=0)
    provenance_binding: str = Field(pattern=r"^archive_digest_only$")
    limitations: list[str] = Field(max_length=20)


def parse_receipt(data):
    return (GCSReceipt if data.get("kind") == "gcs" else Receipt).model_validate(data)


def admit(spec, root):
    if not spec.acquisition_receipt:
        return spec
    with open_scoped_source(spec.acquisition_receipt, root) as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != spec.acquisition_sha256:
        raise VeriFlowError("Acquisition receipt size or digest mismatch")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError()
        receipt = parse_receipt(data)
        if receipt.repo_id != spec.repo_id or receipt.archive_sha256 != spec.sha256:
            raise ValueError()
        if isinstance(receipt, GCSReceipt):
            if any(ord(c) < 32 or ord(c) == 127 for c in receipt.object):
                raise ValueError()
        else:
            validate_remote(
                receipt.url, receipt.requested_revision, [urlsplit(receipt.url).hostname or ""]
            )
            if (
                receipt.coverage_verified
                or len({f.path for f in receipt.files}) != len(receipt.files)
                or sum(f.size_bytes for f in receipt.files) != receipt.source_bytes
            ):
                raise ValueError()
    except (ValidationError, ValueError):
        raise VeriFlowError("Acquisition receipt identity or structure mismatch") from None
    return spec.model_copy(update={"acquisition_data": receipt.model_dump(mode="json")})


def verify_snapshot(spec, manifest):
    if not spec.acquisition_data:
        return
    receipt = parse_receipt(spec.acquisition_data)
    if isinstance(receipt, GCSReceipt):
        if (
            receipt.archive_sha256 != manifest.archive_sha256
            or receipt.size != manifest.archive_size_bytes
        ):
            raise VeriFlowError("Captured archive differs from GCS receipt")
        return
    expected = {f.path: (f.size_bytes, f.sha256) for f in receipt.files}
    actual = {f.path: (f.size_bytes, f.sha256) for f in manifest.files}
    if expected != actual:
        raise VeriFlowError("Captured source differs from acquisition receipt file inventory")


def summary(spec, bound=False):
    data = (spec or {}).get("acquisition_data")
    if not data:
        return None
    receipt = parse_receipt(data)
    if isinstance(receipt, GCSReceipt):
        return dict(
            kind="gcs",
            state="snapshot_bound" if bound else "admitted",
            bucket=receipt.bucket,
            object=receipt.object,
            generation=receipt.generation,
            archive_sha256=receipt.archive_sha256,
            archive_size_bytes=receipt.size,
            receipt_sha256=spec["acquisition_sha256"],
            remote_history_authenticated=False,
            scope="Operator-supplied receipt; captured archive digest/size binding only",
        )
    return dict(
        kind="git",
        state="snapshot_bound" if bound else "admitted",
        url=receipt.url,
        requested_revision=receipt.requested_revision,
        resolved_commit=receipt.resolved_commit,
        archive_sha256=receipt.archive_sha256,
        receipt_sha256=spec["acquisition_sha256"],
        git_version=receipt.git_version,
        source_files=len(receipt.files),
        source_bytes=receipt.source_bytes,
        remote_history_authenticated=False,
        scope="Operator-supplied receipt; archive and snapshot content binding only",
    )
