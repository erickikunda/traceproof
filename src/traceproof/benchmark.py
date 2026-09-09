"""Evaluator-only benchmark contracts. Scan workers never import or receive labels."""

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from traceproof.bundles import canonical
from traceproof.domain import Digest, Identifier, TraceProofError
from traceproof.persistence import Snapshot

MAX_DOCUMENT_BYTES = 1024 * 1024


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class BenchmarkRepository(StrictContract):
    repo_id: Identifier
    snapshot_id: Digest
    languages: list[Identifier] = Field(min_length=1, max_length=20)
    weakness_scope: list[Annotated[str, Field(pattern=r"^CWE-[1-9][0-9]*$")]] = Field(
        min_length=1, max_length=200
    )
    label_coverage: Literal["known_positives_only", "exhaustive_for_declared_scope"]


class BenchmarkManifest(StrictContract):
    schema_version: Literal["1"]
    dataset_id: Identifier
    dataset_version: Identifier
    repositories: list[BenchmarkRepository] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_repositories(self):
        if len({item.repo_id for item in self.repositories}) != len(self.repositories):
            raise ValueError("Duplicate repository identity")
        for item in self.repositories:
            if len(set(item.languages)) != len(item.languages) or len(
                set(item.weakness_scope)
            ) != len(item.weakness_scope):
                raise ValueError("Duplicate scope entry")
        return self


class BenchmarkLabel(StrictContract):
    label_id: Identifier
    repo_id: Identifier
    snapshot_id: Digest
    root_cause_id: Identifier
    cwe: Annotated[str, Field(pattern=r"^CWE-[1-9][0-9]*$")]
    path: str = Field(min_length=1, max_length=512)
    file_sha256: Digest
    line: int = Field(ge=1, le=10000000)
    end_line: int = Field(ge=1, le=10000000)
    symbol: str = Field(min_length=1, max_length=512)
    adjudication_reference: str = Field(min_length=1, max_length=1000)

    @field_validator("path")
    @classmethod
    def relative_path(cls, value):
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or "\\" in value
            or "\x00" in value
            or str(path) != value
        ):
            raise ValueError("Expected normalized snapshot-relative path")
        return value

    @model_validator(mode="after")
    def nonempty_and_ordered(self):
        if (
            self.end_line < self.line
            or not self.symbol.strip()
            or not self.adjudication_reference.strip()
        ):
            raise ValueError("Invalid location or provenance")
        return self


class BenchmarkLabels(StrictContract):
    schema_version: Literal["1"]
    dataset_id: Identifier
    label_set_version: Identifier
    manifest_sha256: Digest
    labels: list[BenchmarkLabel] = Field(max_length=20000)

    @model_validator(mode="after")
    def unique_labels(self):
        if len({item.label_id for item in self.labels}) != len(self.labels):
            raise ValueError("Duplicate label identity")
        units = {(item.repo_id, item.snapshot_id, item.root_cause_id) for item in self.labels}
        if len(units) != len(self.labels):
            raise ValueError("One label per root-cause unit is required")
        return self


def read_contract(path, contract):
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_DOCUMENT_BYTES + 1)
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise TraceProofError("Benchmark document exceeds 1 MiB")
    try:
        # Reject duplicate JSON keys rather than silently overwriting label/scope fields.
        def object_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON key")
                result[key] = value
            return result

        value = json.loads(raw, object_pairs_hook=object_pairs)
        return contract.model_validate(value)
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise TraceProofError(
            "Invalid benchmark document; check schema, identities and ranges"
        ) from None


def check_benchmark(manifest_path, labels_path=None, store=None):
    manifest = read_contract(manifest_path, BenchmarkManifest)
    manifest_digest = hashlib.sha256(canonical(manifest.model_dump())).hexdigest()
    labels = read_contract(labels_path, BenchmarkLabels) if labels_path else None
    repositories = {item.repo_id: item for item in manifest.repositories}
    if labels:
        if labels.dataset_id != manifest.dataset_id or labels.manifest_sha256 != manifest_digest:
            raise TraceProofError("Label set does not match the pinned benchmark manifest")
        for label in labels.labels:
            repository = repositories.get(label.repo_id)
            if (
                repository is None
                or label.snapshot_id != repository.snapshot_id
                or label.cwe not in repository.weakness_scope
            ):
                raise TraceProofError(
                    "Label repository, snapshot or weakness is outside manifest scope"
                )
    issues = []
    aligned = 0
    if store is not None:
        with store.transaction() as session:
            for repository in manifest.repositories:
                snapshot = session.get(Snapshot, repository.snapshot_id)
                if snapshot is None or snapshot.repo_id != repository.repo_id:
                    issues.append(
                        {
                            "repo_id": repository.repo_id,
                            "code": "snapshot_missing_or_wrong_repository",
                        }
                    )
                    continue
                files = {item["path"]: item["sha256"] for item in snapshot.manifest["files"]}
                failures = [
                    label
                    for label in (labels.labels if labels else [])
                    if label.repo_id == repository.repo_id
                    and files.get(label.path) != label.file_sha256
                ]
                if failures:
                    issues.append(
                        {
                            "repo_id": repository.repo_id,
                            "code": "label_file_missing_or_digest_mismatch",
                            "label_count": len(failures),
                        }
                    )
                else:
                    aligned += 1
    label_digest = hashlib.sha256(canonical(labels.model_dump())).hexdigest() if labels else None
    return {
        "schema_version": "1",
        "report_kind": "benchmark_contract_check",
        "dataset_id": manifest.dataset_id,
        "dataset_version": manifest.dataset_version,
        "manifest_sha256": manifest_digest,
        "labels_sha256": label_digest,
        "repository_count": len(repositories),
        "label_count": len(labels.labels) if labels else None,
        "labels_supplied": labels is not None,
        "local_alignment_checked": store is not None,
        "aligned_repositories": aligned if store is not None else None,
        "status": "alignment_incomplete" if issues else "valid_contract",
        "issues": issues,
        "evaluation_performed": False,
        "precision": None,
        "recall": None,
        "limitations": [
            "Contract validation does not verify vulnerability truth or label completeness.",
            "Alignment checks stored digests, not source bytes or line semantics.",
            "Unlisted findings remain unjudged, not automatic false positives.",
            "Labels are evaluator inputs; never include them in source archives or scan requests.",
        ],
    }
