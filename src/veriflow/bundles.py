"""Deterministic, bounded evidence bundles from immutable scan results."""

import hashlib
import io
import json
import tokenize
from pathlib import Path

from sqlalchemy import select

from veriflow.domain import VeriFlowError
from veriflow.indexing import verified_source
from veriflow.joern_claims import RULE_POLICIES, native_audit
from veriflow.persistence import Candidate, EvidenceBundle, ScanAttempt, exclusive_worker
from veriflow.python_parser import MAX_BYTES
from veriflow.sarif import MAX_SARIF_BYTES, bind_location, fingerprint, indexed

BUILDER_VERSION = "13"
MAX_LOCATIONS = 8
MAX_BUNDLE_BYTES = 32 * 1024
MAX_SOURCE_BYTES = 16 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def get_bundle(store, bundle_id):
    with store.transaction() as session:
        bundle = session.get(EvidenceBundle, bundle_id)
        if bundle is None:
            raise VeriFlowError("Evidence bundle not found")
        if hashlib.sha256(canonical(bundle.content)).hexdigest() != bundle.id:
            raise VeriFlowError("Evidence bundle digest mismatch")
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
        raise VeriFlowError("Scan candidate not found")
    run, manifest, tree = verified_source(store, attempt.run_id)
    if candidate.evidence.get("origin") == "llm_discovery":
        return _build_llm_bundle(
            store, attempt, candidate, run, manifest, tree, candidate_fingerprint
        )
    raw_path = store.root / "scans" / attempt.id / "results.sarif"
    if (
        Path(attempt.report["raw_sarif_path"]).resolve() != raw_path.resolve()
        or raw_path.is_symlink()
    ):
        raise VeriFlowError("Unexpected SARIF artifact path")
    with raw_path.open("rb") as handle:
        raw = handle.read(MAX_SARIF_BYTES + 1)
    if len(raw) > MAX_SARIF_BYTES or hashlib.sha256(raw).hexdigest() != attempt.report.get(
        "sarif_sha256"
    ):
        raise VeriFlowError("SARIF integrity check failed")
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
            raise VeriFlowError("Candidate is absent from pinned SARIF")
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
        location_limit = MAX_LOCATIONS + int(
            candidate.evidence["rule_id"] == "veriflow/joern-rust-env-shell-v1"
            and attempt.report.get("scanner", {}).get("engine_id") == "joern"
        )
        references = [
            (role, bind_location(location, sarif_run, manifest, tree), metadata)
            for role, location, metadata in locations[:location_limit]
        ]
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, RecursionError):
        raise VeriFlowError("Cannot interpret candidate SARIF evidence") from None
    snippets, gaps, source_bytes = [], [], 0
    if not result.get("locations"):
        gaps.append("primary_location_missing")
    if not references:
        gaps.append("no_locations")
    if len(locations) > location_limit:
        gaps.append("location_limit")
    for position, (role, reference, metadata) in enumerate(references):
        if reference is None:
            gaps.append(f"location_{position}:unmapped")
            continue
        try:
            record = next(file for file in manifest.files if file.path == reference["path"])
            if record.size_bytes > MAX_BYTES:
                raise VeriFlowError("file_limit")
            with (tree / record.path).open("rb") as handle:
                contents = handle.read(MAX_BYTES + 1)
            if hashlib.sha256(contents).hexdigest() != record.sha256:
                raise VeriFlowError("source_integrity")
            encoding = tokenize.detect_encoding(io.BytesIO(contents).readline)[0]
            lines = io.StringIO(contents.decode(encoding), newline="").readlines()
            start, end = reference["line"], reference["end_line"]
            if end > len(lines) or end - start + 1 > 40:
                raise VeriFlowError("range_limit")
            start, end = max(1, start - 3), min(len(lines), end + 3)
            # Small Java/C# files retain imports and declaration context for syntax gates.
            # Existing cumulative source/envelope limits still apply.
            if len(lines) <= 40 and (
                record.path.endswith((".java", ".cs"))
                or (
                    record.path.endswith(
                        (".py", ".js", ".ts", ".go", ".rs", ".c", ".h", ".cpp", ".hpp")
                    )
                    and candidate.evidence["rule_id"] in RULE_POLICIES
                    and attempt.report.get("scanner", {}).get("engine_id") == "joern"
                )
            ):
                start, end = 1, len(lines)
            text = "".join(lines[start - 1 : end])
            size = len(text.encode())
            if source_bytes + size > MAX_SOURCE_BYTES:
                raise VeriFlowError("source_budget")
            source_bytes += size
            snippets.append(
                {
                    "id": f"E{position + 1}",
                    "role": role,
                    **metadata,
                    **reference,
                    "excerpt_line": start,
                    "excerpt_end_line": end,
                    "source_line_count": len(lines),
                    "text": text,
                }
            )
        except VeriFlowError as exc:
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
        "engine_id": (
            attempt.report["scanner"].get("engine_id", "unknown")
            if isinstance(attempt.report.get("scanner"), dict)
            else "codeql"
            if "scanner" not in attempt.report
            else "unknown"
        ),
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
    if content["engine_id"] == "joern" and content["rule_id"] in RULE_POLICIES:
        content["joern_native_audit"] = native_audit(
            store.root / "scans" / attempt.id,
            attempt.report,
            manifest,
            tree,
            raw,
            result,
            policy=RULE_POLICIES[content["rule_id"]],
        )
    if len(canonical(content)) > MAX_BUNDLE_BYTES:
        raise VeriFlowError("Evidence bundle exceeds the 32 KiB envelope limit")
    verified_source(store, run.id)
    identity = hashlib.sha256(canonical(content)).hexdigest()
    with store.transaction() as session:
        if session.get(EvidenceBundle, identity) is None:
            session.add(EvidenceBundle(id=identity, candidate_id=candidate.id, content=content))
    return get_bundle(store, identity)


def _build_llm_bundle(store, attempt, candidate, run, manifest, tree, candidate_fingerprint):
    """Build snapshot-bound evidence without pretending the proposal came from SARIF."""
    proposal = candidate.evidence.get("llm_discovery", {})
    locations = proposal.get("locations", [])
    if not locations or len(locations) > MAX_LOCATIONS:
        raise VeriFlowError("LLM discovery candidate has invalid location count")
    records = {record.path: record for record in manifest.files}
    snippets, gaps, source_bytes = [], [], 0
    for position, location in enumerate(locations):
        try:
            record = records.get(location["path"])
            if (
                record is None
                or record.sha256 != location["sha256"]
                or type(location["line"]) is not int
                or type(location["end_line"]) is not int
                or not 1 <= location["line"] <= location["end_line"]
                or location["end_line"] - location["line"] >= 40
            ):
                raise VeriFlowError("unverified_location")
            payload = (tree / record.path).read_bytes()
            if hashlib.sha256(payload).hexdigest() != record.sha256:
                raise VeriFlowError("source_integrity")
            lines = payload.decode("utf-8").splitlines(keepends=True)
            if location["end_line"] > len(lines):
                raise VeriFlowError("range_limit")
            start = max(1, location["line"] - 3)
            end = min(len(lines), location["end_line"] + 3)
            text = "".join(lines[start - 1 : end])
            size = len(text.encode())
            if source_bytes + size > MAX_SOURCE_BYTES:
                raise VeriFlowError("source_budget")
            source_bytes += size
            snippets.append(
                {
                    "id": f"E{position + 1}",
                    "role": location["role"],
                    "snapshot_id": manifest.snapshot_id,
                    "path": record.path,
                    "sha256": record.sha256,
                    "line": location["line"],
                    "end_line": location["end_line"],
                    "excerpt_line": start,
                    "excerpt_end_line": end,
                    "source_line_count": len(lines),
                    "text": text,
                }
            )
        except VeriFlowError as exc:
            if str(exc) == "source_integrity":
                raise
            gaps.append(f"location_{position}:{exc}")
        except (KeyError, TypeError, UnicodeError):
            gaps.append(f"location_{position}:invalid")
    content = {
        "schema_version": "1",
        "builder_version": BUILDER_VERSION,
        "engine_id": "llm_discovery",
        "expansion_depth": 0,
        "run_id": run.id,
        "repo_id": run.repo_id,
        "snapshot_id": manifest.snapshot_id,
        "classification": manifest.classification,
        "attempt_id": attempt.id,
        "candidate_fingerprint": candidate_fingerprint,
        "rule_id": candidate.evidence["rule_id"],
        "message": candidate.evidence["message"][:2048],
        "suppressed": False,
        "sarif_sha256": None,
        "discovery_proposal_sha256": proposal.get("proposal_sha256"),
        "cwe": candidate.evidence.get("cwe"),
        "snippets": snippets,
        "gaps": gaps,
        "status": "partial" if gaps or not snippets else "ready",
        "locations_total": len(locations),
        "locations_considered": len(locations),
        "trust": "untrusted_source_and_model_proposal",
        "reachability_proven": False,
    }
    if len(canonical(content)) > MAX_BUNDLE_BYTES:
        raise VeriFlowError("Evidence bundle exceeds the 32 KiB envelope limit")
    verified_source(store, run.id)
    identity = hashlib.sha256(canonical(content)).hexdigest()
    with store.transaction() as session:
        if session.get(EvidenceBundle, identity) is None:
            session.add(EvidenceBundle(id=identity, candidate_id=candidate.id, content=content))
    return get_bundle(store, identity)
