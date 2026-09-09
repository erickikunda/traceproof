"""Deterministic, bounded evidence bundles from immutable scan results."""

import hashlib
import io
import json
import tokenize
from pathlib import Path

from sqlalchemy import select

from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.persistence import Candidate, EvidenceBundle, ScanAttempt, exclusive_worker
from traceproof.python_parser import MAX_BYTES
from traceproof.sarif import MAX_SARIF_BYTES, bind_location, fingerprint, indexed

BUILDER_VERSION = "2"
MAX_LOCATIONS = 8
MAX_BUNDLE_BYTES = 32 * 1024
MAX_SOURCE_BYTES = 16 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def get_bundle(store, bundle_id):
    with store.transaction() as session:
        bundle = session.get(EvidenceBundle, bundle_id)
        if bundle is None:
            raise TraceProofError("Evidence bundle not found")
        if hashlib.sha256(canonical(bundle.content)).hexdigest() != bundle.id:
            raise TraceProofError("Evidence bundle digest mismatch")
        return {"bundle_id": bundle.id, **bundle.content}


def build_bundle(store, attempt_id, candidate_fingerprint):
    store.require_initialized()
    with exclusive_worker(store.root):
        return _build_bundle(store, attempt_id, candidate_fingerprint)


def _build_bundle(store, attempt_id, candidate_fingerprint):
    with store.transaction() as session:
        attempt = session.get(ScanAttempt, attempt_id)
        candidate = session.scalar(
            select(Candidate).where(
                Candidate.attempt_id == attempt_id, Candidate.fingerprint == candidate_fingerprint
            )
        )
        if attempt is None or candidate is None:
            raise TraceProofError("Scan candidate not found")
    run, manifest, tree = verified_source(store, attempt.run_id)
    raw_path = store.root / "scans" / attempt.id / "results.sarif"
    if (
        Path(attempt.report["raw_sarif_path"]).resolve() != raw_path.resolve()
        or raw_path.is_symlink()
    ):
        raise TraceProofError("Unexpected SARIF artifact path")
    with raw_path.open("rb") as handle:
        raw = handle.read(MAX_SARIF_BYTES + 1)
    if len(raw) > MAX_SARIF_BYTES or hashlib.sha256(raw).hexdigest() != attempt.report.get(
        "sarif_sha256"
    ):
        raise TraceProofError("SARIF integrity check failed")
    matched = None
    try:
        for sarif_run in json.loads(raw)["runs"]:
            driver = sarif_run["tool"]["driver"]
            for result in sarif_run.get("results", []):
                rule = result.get("ruleId") or indexed(driver["rules"], result["ruleIndex"])["id"]
                if fingerprint(manifest.snapshot_id, driver, rule, result) == candidate_fingerprint:
                    matched = sarif_run, result
                    break
            if matched:
                break
        if matched is None:
            raise TraceProofError("Candidate is absent from pinned SARIF")
        sarif_run, result = matched
        # Preserve primary locations and every flow in SARIF order; cap materialized snippets.
        locations = [
            ("primary", item.get("physicalLocation", {}), {})
            for item in result.get("locations", [])
        ]
        for flow_number, flow in enumerate(result.get("codeFlows", [])):
            for thread_number, thread in enumerate(flow.get("threadFlows", [])):
                steps = thread.get("locations", [])
                locations.extend(
                    (
                        "flow",
                        item.get("location", {}).get("physicalLocation", {}),
                        {
                            "flow_id": f"F{flow_number}T{thread_number}",
                            "flow_step": step,
                            "flow_steps": len(steps),
                        },
                    )
                    for step, item in enumerate(steps)
                )
        for location in result.get("relatedLocations", []):
            locations.append(("related", location.get("physicalLocation", {}), {}))
        references = [
            (role, bind_location(location, sarif_run, manifest, tree), metadata)
            for role, location, metadata in locations[:MAX_LOCATIONS]
        ]
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, RecursionError):
        raise TraceProofError("Cannot interpret candidate SARIF evidence") from None
    snippets, gaps, source_bytes = [], [], 0
    if not result.get("locations"):
        gaps.append("primary_location_missing")
    if not references:
        gaps.append("no_locations")
    if len(locations) > MAX_LOCATIONS:
        gaps.append("location_limit")
    for position, (role, reference, metadata) in enumerate(references):
        if reference is None:
            gaps.append(f"location_{position}:unmapped")
            continue
        try:
            record = next(file for file in manifest.files if file.path == reference["path"])
            if record.size_bytes > MAX_BYTES:
                raise TraceProofError("file_limit")
            with (tree / record.path).open("rb") as handle:
                contents = handle.read(MAX_BYTES + 1)
            if hashlib.sha256(contents).hexdigest() != record.sha256:
                raise TraceProofError("source_integrity")
            encoding = tokenize.detect_encoding(io.BytesIO(contents).readline)[0]
            lines = io.StringIO(contents.decode(encoding), newline="").readlines()
            start, end = reference["line"], reference["end_line"]
            if end > len(lines) or end - start + 1 > 40:
                raise TraceProofError("range_limit")
            start, end = max(1, start - 3), min(len(lines), end + 3)
            text = "".join(lines[start - 1 : end])
            size = len(text.encode())
            if source_bytes + size > MAX_SOURCE_BYTES:
                raise TraceProofError("source_budget")
            source_bytes += size
            snippets.append(
                {
                    "id": f"E{position + 1}",
                    "role": role,
                    **metadata,
                    **reference,
                    "excerpt_line": start,
                    "excerpt_end_line": end,
                    "text": text,
                }
            )
        except TraceProofError as exc:
            if str(exc) == "source_integrity":
                raise
            gaps.append(f"location_{position}:{exc}")
        except (UnicodeError, SyntaxError, LookupError):
            gaps.append(f"location_{position}:encoding")
    message = candidate.evidence["message"]
    if len(message.encode()) > 2048:
        message = message.encode()[:2048].decode(errors="ignore")
        gaps.append("message_limit")
    content = {
        "schema_version": "1",
        "builder_version": BUILDER_VERSION,
        "expansion_depth": 0,
        "run_id": run.id,
        "repo_id": run.repo_id,
        "snapshot_id": manifest.snapshot_id,
        "classification": manifest.classification,
        "attempt_id": attempt_id,
        "candidate_fingerprint": candidate_fingerprint,
        "rule_id": candidate.evidence["rule_id"],
        "message": message,
        "suppressed": candidate.evidence["suppressed"],
        "sarif_sha256": attempt.report["sarif_sha256"],
        "snippets": snippets,
        "gaps": gaps,
        "status": "partial" if gaps else "ready",
        "locations_total": len(locations),
        "locations_considered": len(references),
        "trust": "untrusted_source_and_tool_output",
        "reachability_proven": False,
    }
    if len(canonical(content)) > MAX_BUNDLE_BYTES:
        raise TraceProofError("Evidence bundle exceeds the 32 KiB envelope limit")
    verified_source(store, run.id)
    identity = hashlib.sha256(canonical(content)).hexdigest()
    with store.transaction() as session:
        if session.get(EvidenceBundle, identity) is None:
            session.add(EvidenceBundle(id=identity, candidate_id=candidate.id, content=content))
    return get_bundle(store, identity)
