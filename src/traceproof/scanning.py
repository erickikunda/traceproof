"""Offline CodeQL queries, durable diagnostics and atomic candidate publication."""

import hashlib
import html
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from traceproof.codeql import extraction_status
from traceproof.codeql_resources import resource_settings
from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.intake import now
from traceproof.persistence import Candidate, Run, ScanAttempt
from traceproof.sarif import MAX_SARIF_BYTES, normalize


def query_entry(store, queries):
    queries = Path(queries).resolve(strict=True)
    if not queries.is_file() or queries.suffix not in {".ql", ".qls"}:
        raise TraceProofError("Provide a trusted local .ql query or .qls suite")
    if queries.is_relative_to(store.root / "artifacts"):
        raise TraceProofError("Queries must come from operator tooling, not scanned source")
    return queries


def analyze(store, extraction_id, queries, timeout=600, *, threads=2, ram_mb=2048):
    """Caller holds exclusive_worker. queries is a trusted operator-supplied local file."""
    resources = resource_settings(threads, ram_mb)
    if not 1 <= timeout <= 3600:
        raise TraceProofError("Query timeout must be between 1 and 3600 seconds")
    extraction = extraction_status(store, extraction_id)
    if extraction["status"] != "extracted":
        raise TraceProofError("Security queries require a successful extraction")
    run, manifest, tree = verified_source(store, extraction["run_id"])
    queries = query_entry(store, queries)
    attempt_id = str(uuid4())
    root = store.root / "scans" / attempt_id
    root.mkdir(parents=True, mode=0o700)
    with queries.open("rb") as handle:
        query_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        "schema_version": "1",
        "report_kind": "static_candidates",
        "attempt_id": attempt_id,
        "run_id": run.id,
        "repo_id": run.repo_id,
        "snapshot_id": manifest.snapshot_id,
        "classification": manifest.classification,
        "extraction_id": extraction_id,
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
    executable = shutil.which("codeql")
    started = time.monotonic()
    candidates = []
    if executable is None:
        report["status"] = "unavailable"
    else:
        env = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(root),
            "TMPDIR": str(root),
            "LANG": "en_US.UTF-8",
        }
        try:
            version = subprocess.run(
                [executable, "version", "--format=json"],
                env=env,
                cwd=root,
                capture_output=True,
                timeout=10,
                check=True,
            )
            report["analysis_codeql_version"] = json.loads(version.stdout)["version"]
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            report["analysis_codeql_version"] = "unknown"
        command = [
            executable,
            "database",
            "analyze",
            extraction["database_path"],
            "path:" + str(queries),
            "--format=sarifv2.1.0",
            "--no-download",
            "--no-sarif-add-file-contents",
            "--no-sarif-add-snippets",
            f"--output={root / 'results.sarif'}",
            f"--threads={threads}",
            f"--ram={ram_mb}",
            f"--common-caches={root / 'cache'}",
        ]
        with (root / "analyze.log").open("wb") as log:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                try:
                    code = process.wait(timeout=timeout)
                    report.update(exit_code=code, status="query_failed" if code else "completed")
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    report["status"] = "timeout"
            except OSError:
                report["status"] = "launch_failed"
        if report["status"] == "completed":
            try:
                verified_source(store, run.id)
                with queries.open("rb") as handle:
                    if hashlib.file_digest(handle, "sha256").hexdigest() != query_digest:
                        raise TraceProofError("Query entry file changed during analysis")
                with (root / "results.sarif").open("rb") as handle:
                    raw = handle.read(MAX_SARIF_BYTES + 1)
                candidates, summary = normalize(raw, manifest, tree)
                report.update(summary, sarif_sha256=hashlib.sha256(raw).hexdigest())
                if not summary["execution_complete"] or summary["unmapped_candidates"]:
                    report["status"] = "partial"
            except (TraceProofError, OSError):
                report["status"] = "invalid_output_or_integrity"
                candidates = []
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
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
