"""Explicit operator assertions, separate from raw candidates and model proposals."""

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import func, select

from veriflow.bundles import canonical, get_bundle
from veriflow.domain import Digest, VeriFlowError
from veriflow.intake import now
from veriflow.persistence import (
    Candidate,
    EvidenceBundle,
    OperatorReview,
    Run,
    ScanAttempt,
    exclusive_worker,
)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    reviewer_label: str = Field(min_length=1, max_length=100)
    state: Literal["confirmed", "false_positive", "needs_review", "deferred"]
    rationale: str = Field(min_length=1, max_length=2000)
    bundle_id: Digest
    evidence_ids: list[Annotated[str, Field(pattern=r"^E[1-9][0-9]*$", max_length=20)]] = Field(
        max_length=8
    )
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.reviewer_label.strip() or not self.rationale.strip():
            raise ValueError("Reviewer and rationale must be nonblank")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Evidence IDs must be unique")
        if self.state in {"confirmed", "false_positive"} and not self.evidence_ids:
            raise ValueError("Definitive assertions require cited evidence")
        return self


def read_review(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(16 * 1024 + 1)
    if len(raw) > 16 * 1024:
        raise VeriFlowError("Review request exceeds 16 KiB")
    try:

        def object_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON key")
                result[key] = value
            return result

        return ReviewRequest.model_validate(json.loads(raw, object_pairs_hook=object_pairs))
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise VeriFlowError("Invalid review request; check schema, state and evidence") from None


def selected_candidate(session, repo_id, attempt_id, fingerprint):
    candidate = session.scalar(
        select(Candidate)
        .join(ScanAttempt)
        .join(Run)
        .where(
            Run.repo_id == repo_id,
            ScanAttempt.id == attempt_id,
            Candidate.fingerprint == fingerprint,
        )
    )
    if candidate is None:
        raise VeriFlowError("Candidate does not belong to repository/attempt")
    return candidate


def verified_review(record):
    if (
        hashlib.sha256(canonical(record.content)).hexdigest() != record.id
        or record.content["candidate_id"] != record.candidate_id
        or record.content["revision"] != record.revision
        or record.content["request_sha256"] != record.request_sha256
        or record.content["bundle_id"] != record.bundle_id
    ):
        raise VeriFlowError("Operator review integrity check failed")
    return {"review_id": record.id, **record.content}


def record_review(store, repo_id, attempt_id, fingerprint, request, key):
    if not isinstance(request, ReviewRequest):
        raise VeriFlowError("Expected a validated review request")
    try:
        request = ReviewRequest.model_validate(request.model_dump())
    except ValidationError:
        raise VeriFlowError("Invalid review request; check schema, state and evidence") from None
    if not key.strip() or len(key) > 200:
        raise VeriFlowError("Review key must contain 1–200 characters")
    store.require_initialized()
    digest = hashlib.sha256(canonical(request.model_dump())).hexdigest()
    with exclusive_worker(store.root), store.transaction() as session:
        candidate = selected_candidate(session, repo_id, attempt_id, fingerprint)
        existing = session.scalar(
            select(OperatorReview).where(
                OperatorReview.candidate_id == candidate.id, OperatorReview.request_key == key
            )
        )
        if existing:
            if existing.request_sha256 != digest:
                raise VeriFlowError("Review key was used for a different request")
            return verified_review(existing)
        revision = (
            session.scalar(
                select(func.max(OperatorReview.revision)).where(
                    OperatorReview.candidate_id == candidate.id
                )
            )
            or 0
        )
        if request.expected_revision != revision:
            raise VeriFlowError(
                "Stale review revision; retrieve history before submitting a new decision"
            )
        bundle_record = session.get(EvidenceBundle, request.bundle_id)
        if bundle_record is None or bundle_record.candidate_id != candidate.id:
            raise VeriFlowError("Review bundle does not belong to the candidate")
        bundle = get_bundle(store, request.bundle_id)
        if set(request.evidence_ids) - {item["id"] for item in bundle["snippets"]}:
            raise VeriFlowError("Review cites evidence absent from its bundle")
        if request.state in {"confirmed", "false_positive"} and bundle["status"] != "ready":
            raise VeriFlowError("Definitive review requires a ready evidence bundle")
        content = {
            "schema_version": "1",
            "candidate_id": candidate.id,
            "revision": revision + 1,
            "created_at": now(),
            "request_sha256": digest,
            **request.model_dump(exclude={"expected_revision"}),
            "reviewer_authenticated": False,
            "independently_verified": False,
        }
        identity = hashlib.sha256(canonical(content)).hexdigest()
        record = OperatorReview(
            id=identity,
            candidate_id=candidate.id,
            bundle_id=request.bundle_id,
            revision=revision + 1,
            request_key=key,
            request_sha256=digest,
            content=content,
        )
        session.add(record)
        return verified_review(record)


def review_history(store, repo_id, attempt_id, fingerprint, offset=0, limit=100):
    if offset < 0 or not 1 <= limit <= 1000:
        raise VeriFlowError("Invalid review pagination")
    with store.transaction() as session:
        candidate = selected_candidate(session, repo_id, attempt_id, fingerprint)
        query = select(OperatorReview).where(OperatorReview.candidate_id == candidate.id)
        records = session.scalars(
            query.order_by(OperatorReview.revision).offset(offset).limit(limit)
        )
        current = (
            session.scalar(
                select(func.max(OperatorReview.revision)).where(
                    OperatorReview.candidate_id == candidate.id
                )
            )
            or 0
        )
        return {
            "repo_id": repo_id,
            "attempt_id": attempt_id,
            "fingerprint": fingerprint,
            "current_revision": current,
            "offset": offset,
            "limit": limit,
            "reviews": [verified_review(record) for record in records],
        }
