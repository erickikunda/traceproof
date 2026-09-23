"""Versioned intake contracts; intake readiness is not scan completion."""

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VeriFlowError(Exception):
    """An expected failure safe to present without a stack trace."""


class ItemState(StrEnum):
    READY = "ready"
    PROCESSING = "processing"
    SNAPSHOTTED = "snapshotted"
    REJECTED = "rejected"
    FAILED = "failed"


class RunState(StrEnum):
    ADMITTED = "admitted"
    SNAPSHOTTED = "snapshotted"
    FAILED = "failed"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class IntakeSpec(Contract):
    repo_id: Identifier
    source_type: Literal["pvc"]
    source_uri: Annotated[str, Field(min_length=1, max_length=4096)]
    owner: Annotated[str, Field(min_length=1, max_length=200)]
    classification: Annotated[str, Field(min_length=1, max_length=100)]
    sha256: Digest | None = None
    scan_profile: Literal["standard"] = "standard"
    acquisition_receipt: str | None = None
    acquisition_sha256: Digest | None = None
    acquisition_data: dict | None = None

    @model_validator(mode="after")
    def receipt_pair(self):
        if bool(self.acquisition_receipt) != bool(self.acquisition_sha256):
            raise ValueError("Acquisition receipt path and digest must be supplied together")
        if self.acquisition_receipt and (
            not self.acquisition_receipt.startswith("/") or not self.sha256
        ):
            raise ValueError("Acquisition receipt requires an absolute path and archive SHA-256")
        return self

    @field_validator("source_uri")
    @classmethod
    def absolute_local_path(cls, value: str) -> str:
        if not value.startswith("/") or "\x00" in value:
            raise ValueError("source_uri must be an absolute local archive path")
        return value


class FileRecord(Contract):
    path: str
    size_bytes: Annotated[int, Field(ge=0)]
    sha256: Digest

    @field_validator("path")
    @classmethod
    def relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("file reference must stay inside the source snapshot")
        return value


class SnapshotManifest(Contract):
    schema_version: Literal["1"] = "1"
    snapshot_id: Digest
    repo_id: Identifier
    classification: str
    archive_sha256: Digest
    archive_size_bytes: Annotated[int, Field(gt=0)]
    files: tuple[FileRecord, ...]


class ArchiveLimits(Contract):
    max_archive_bytes: Annotated[int, Field(gt=0)] = 256 * 1024 * 1024
    max_expanded_bytes: Annotated[int, Field(gt=0)] = 1024 * 1024 * 1024
    max_members: Annotated[int, Field(gt=0)] = 20_000
    max_path_bytes: Annotated[int, Field(gt=0)] = 512
    max_path_depth: Annotated[int, Field(gt=0)] = 30
    max_compression_ratio: Annotated[int, Field(gt=0)] = 200
