"""Offline CodeQL queries, durable diagnostics and atomic candidate publication."""

import hashlib
import html
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from traceproof.codeql_resources import resource_settings
from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.intake import now
from traceproof.persistence import Candidate, Run, ScanAttempt
from traceproof.sarif import MAX_SARIF_BYTES, normalize
from traceproof.scan_identity import analysis_identity
from traceproof.scanner import ExecutionRequest
from traceproof.scanner_backends import PreparedInput, backend_for


def query_entry(store, queries):
    queries = Path(queries).resolve(strict=True)
    if not queries.is_file() or queries.suffix not in {".ql", ".qls"}:
        raise TraceProofError("Provide a trusted local .ql query or .qls suite")
    if queries.is_relative_to(store.root / "artifacts"):
        raise TraceProofError("Queries must come from operator tooling, not scanned source")
    return queries


def analyze(store, extraction_id, queries, timeout=600, *, threads=2, ram_mb=2048, engine="codeql"):
    """Caller holds exclusive_worker. queries is a trusted operator-supplied local file."""
    backend = backend_for(engine)
    resources = resource_settings(threads, ram_mb)
    if not 1 <= timeout <= 3600:
        raise TraceProofError("Query timeout must be between 1 and 3600 seconds")
    extraction = backend.prepared(store, extraction_id)
    run, manifest, tree = verified_source(store, extraction["run_id"])
    queries = query_entry(store, queries)
    attempt_id = str(uuid4())
    root = store.root / "scans" / attempt_id
    root.mkdir(parents=True, mode=0o700)
    with queries.open("rb") as handle:
        query_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        "scanner": backend.metadata(),
        "prepared_input": PreparedInput(
            backend.engine_id,
            backend.input_kind,
            extraction_id,
            run.id,
            manifest.snapshot_id,
            extraction.get("codeql_version", "unknown"),
        ).metadata(),
        "rule_entry": {
            "engine_id": backend.engine_id,
            "sha256": query_digest,
            "digest_scope": "entry_file_only",
            "transitive_dependencies_verified": False,
        },
        "schema_version": "1",
        "report_kind": "static_candidates",
        "attempt_id": attempt_id,
        "run_id": run.id,
        "repo_id": run.repo_id,
        "snapshot_id": manifest.snapshot_id,
        "classification": manifest.classification,
        "extraction_id": extraction_id,
        "language": extraction.get("language", "python"),
        "language_scope": extraction.get("language_scope"),
        "status": "running",
        "requested_resources": resources,
        "timeout_seconds": timeout,
        "candidate_count": None,
        "verified_finding_count": None,
        "security_verdict": "not_adjudicated",
        "coverage_verified": False,
        "query_path": str(queries),
        "query_sha256": query_digest,
        "extraction_codeql_version": extraction.get("codeql_version", "unknown"),
        "raw_sarif_path": str(root / "results.sarif"),
        "log_path": str(root / "analyze.log"),
        "baseline_requested": extraction.get("baseline_requested", True),
        "limitations": [
            "Candidates have not been verified by a human or LLM.",
            "No-alert output is not a clean security verdict.",
            "Coverage and reachability are not proven.",
            "Query hash covers the entry file, not its transitive dependencies.",
            "Raw SARIF retains flows/diagnostics; records bind only the primary location.",
        ],
    }
    with store.transaction() as session:
        for prior in session.scalars(select(ScanAttempt).where(ScanAttempt.run_id == run.id)):
            if prior.report["status"] == "running":
                prior.report = {**prior.report, "status": "interrupted"}
        session.add(ScanAttempt(id=attempt_id, run_id=run.id, created_at=now(), report=report))
    started = time.monotonic()
    candidates = []
    result = backend.executor(
        ExecutionRequest(
            input_path=Path(extraction["database_path"]),
            rules_path=queries,
            work_dir=root,
            timeout_seconds=timeout,
            threads=threads,
            ram_mb=ram_mb,
        )
    )
    report["scanner"]["version"] = result.version
    report["status"] = result.status
    if result.version is not None:
        report["analysis_codeql_version"] = result.version
    if result.exit_code is not None:
        report["exit_code"] = result.exit_code
    if report["status"] == "completed":
        try:
            verified_source(store, run.id)
            with queries.open("rb") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() != query_digest:
                    raise TraceProofError("Query entry file changed during analysis")
            with result.output_path.open("rb") as handle:
                raw = handle.read(MAX_SARIF_BYTES + 1)
            candidates, summary = normalize(raw, manifest, tree)
            report.update(summary, sarif_sha256=hashlib.sha256(raw).hexdigest())
            if not summary["execution_complete"] or summary["unmapped_candidates"]:
                report["status"] = "partial"
        except (TraceProofError, OSError):
            report["status"] = "invalid_output_or_integrity"
            candidates = []
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    report["analysis_identity"] = analysis_identity(report)
    with store.transaction() as session:
        for candidate in candidates:
            session.add(
                Candidate(
                    id=str(uuid4()),
                    attempt_id=attempt_id,
                    fingerprint=candidate["fingerprint"],
                    evidence=candidate,
                )
            )
        session.get(ScanAttempt, attempt_id).report = report
    return report


def scan_report(store, repo_id, run_id=None, attempt_id=None, offset=0, limit=100):
    if offset < 0 or not 1 <= limit <= 1000:
        raise TraceProofError("Invalid candidate pagination")
    with store.transaction() as session:
        runs = select(Run).where(Run.repo_id == repo_id)
        if run_id:
            runs = runs.where(Run.id == run_id)
        run = session.scalar(runs.order_by(Run.created_at.desc(), Run.id.desc()).limit(1))
        if run is None:
            raise TraceProofError("Repository/run not found")
        attempts = select(ScanAttempt).where(ScanAttempt.run_id == run.id)
        if attempt_id:
            attempts = attempts.where(ScanAttempt.id == attempt_id)
        attempt = session.scalar(
            attempts.order_by(ScanAttempt.created_at.desc(), ScanAttempt.id.desc()).limit(1)
        )
        if attempt is None:
            raise TraceProofError("No static-analysis attempt for the selected run")
        items = list(
            session.scalars(
                select(Candidate.evidence)
                .where(Candidate.attempt_id == attempt.id)
                .order_by(Candidate.fingerprint)
                .offset(offset)
                .limit(limit)
            )
        )
        return {**attempt.report, "candidates": items, "offset": offset, "limit": limit}


def scan_report_markdown(report):
    return "\n".join(
        [
            "# TraceProof static-analysis report",
            "",
            f"Repository: `{report['repo_id']}`; run: `{report['run_id']}`",
            f"Attempt: `{report['attempt_id']}`; status: **{report['status']}**",
            "",
            "**NOT ADJUDICATED — candidates are not verified vulnerabilities.**",
            "",
            f"Candidate count: {report['candidate_count']}; coverage verified: false.",
            f"Showing {len(report['candidates'])} entries starting at offset {report['offset']}.",
            "",
            "```text",
            *[
                html.escape(f"{item['rule_id']} | {item['location_status']} | unreviewed")
                .replace("`", "'")
                .replace("\n", " ")
                for item in report["candidates"]
            ],
            "```",
            "",
            *[f"- {item}" for item in report["limitations"]],
            "",
            "JSON includes messages/evidence references; raw SARIF retains full details.",
        ]
    )
