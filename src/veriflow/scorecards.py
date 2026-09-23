"""Immutable evaluator publications; retrieval never reads labels or runs evaluation."""

import hashlib

from sqlalchemy import func, select

from veriflow.bundles import canonical
from veriflow.domain import TraceProofError
from veriflow.evaluation import evaluate_benchmark
from veriflow.history import validate_page
from veriflow.intake import now
from veriflow.persistence import BenchmarkScorecard, exclusive_worker


def verified(record):
    if (
        hashlib.sha256(canonical(record.content)).hexdigest() != record.id
        or record.content.get("dataset_id") != record.dataset_id
    ):
        raise TraceProofError("Scorecard integrity check failed")
    return {"scorecard_id": record.id, **record.content}


def publish_scorecard(store, manifest, labels, plan):
    store.require_initialized()
    with exclusive_worker(store.root):
        result = evaluate_benchmark(store, manifest, labels, plan)
        content = {key: value for key, value in result.items() if key != "scorecard_id"}
        with store.transaction() as session:
            record = session.get(BenchmarkScorecard, result["scorecard_id"])
            if record is None:
                record = BenchmarkScorecard(
                    id=result["scorecard_id"],
                    dataset_id=result["dataset_id"],
                    created_at=now(),
                    content=content,
                )
                session.add(record)
            return verified(record)


def get_scorecard(store, dataset_id, scorecard_id):
    with store.transaction() as session:
        record = session.get(BenchmarkScorecard, scorecard_id)
        if record is None or record.dataset_id != dataset_id:
            raise TraceProofError("Scorecard does not belong to dataset")
        return verified(record)


def scorecard_history(store, dataset_id, offset=0, limit=100):
    validate_page(offset, limit)
    with store.transaction() as session:
        scope = BenchmarkScorecard.dataset_id == dataset_id
        total = session.scalar(select(func.count()).select_from(BenchmarkScorecard).where(scope))
        records = session.scalars(
            select(BenchmarkScorecard)
            .where(scope)
            .order_by(BenchmarkScorecard.created_at.desc(), BenchmarkScorecard.id.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = []
        for record in records:
            report = verified(record)
            rows.append(
                {
                    "scorecard_id": record.id,
                    "created_at": record.created_at,
                    "dataset_version": report["dataset_version"],
                    "evaluator_version": report["evaluator_version"],
                    "complete": report["complete"],
                }
            )
        return {
            "schema_version": "1",
            "dataset_id": dataset_id,
            "offset": offset,
            "limit": limit,
            "total": total,
            "next_offset": offset + len(rows) if offset + len(rows) < total else None,
            "items": rows,
        }
