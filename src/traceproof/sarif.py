"""Bounded SARIF 2.1 normalization; alerts are candidates, not verified findings."""

import hashlib
import json
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from traceproof.domain import TraceProofError

MAX_SARIF_BYTES = 16 * 1024 * 1024
MAX_RESULTS = 10_000


def indexed(items, index):
    if type(index) is not int or index < 0:
        raise ValueError()
    return items[index]


def bind_location(physical, run, manifest, tree, file_records=None):
    """Bind a SARIF location to the snapshot; line validation is a separate step."""
    artifact = physical.get("artifactLocation", {})
    if "uri" not in artifact and "index" in artifact:
        artifact = indexed(run["artifacts"], artifact["index"])["location"]
    uri = urlsplit(artifact.get("uri", ""))
    path = PurePosixPath(unquote(uri.path))
    if uri.scheme == "file" and not uri.netloc:
        try:
            path = path.relative_to(tree.as_posix())
        except ValueError:
            return None
    if (
        uri.scheme not in {"", "file"}
        or uri.netloc
        or uri.query
        or uri.fragment
        or path.is_absolute()
        or ".." in path.parts
        or artifact.get("uriBaseId") not in {None, "%SRCROOT%"}
    ):
        return None
    record = (
        file_records.get(str(path))
        if file_records is not None
        else next((file for file in manifest.files if file.path == str(path)), None)
    )
    region = physical.get("region", {})
    line, end = region.get("startLine"), region.get("endLine", region.get("startLine"))
    if record and type(line) is int and type(end) is int and 1 <= line <= end:
        return {
            "snapshot_id": manifest.snapshot_id,
            "path": record.path,
            "sha256": record.sha256,
            "line": line,
            "end_line": end,
        }
    return None


def fingerprint(snapshot_id, driver, rule, result):
    return hashlib.sha256(
        json.dumps(
            [snapshot_id, driver.get("name"), rule, result], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def normalize(raw, manifest, tree):
    if len(raw) > MAX_SARIF_BYTES:
        raise TraceProofError("SARIF exceeds the 16 MiB limit")
    try:
        doc = json.loads(raw)
        if doc["version"] != "2.1.0" or not isinstance(doc["runs"], list) or not doc["runs"]:
            raise ValueError()
        candidates, seen = [], set()
        errors = warnings = raw_count = 0
        complete = True
        file_records = {file.path: file for file in manifest.files}
        for run in doc["runs"]:
            driver = run["tool"]["driver"]
            invocations = run.get("invocations", [])
            complete &= bool(invocations) and all(
                invocation.get("executionSuccessful") is True for invocation in invocations
            )
            for invocation in invocations:
                notifications = invocation.get("toolExecutionNotifications", [])
                notifications += invocation.get("toolConfigurationNotifications", [])
                errors += sum(item.get("level") == "error" for item in notifications)
                warnings += sum(item.get("level") == "warning" for item in notifications)
            for result in run.get("results", []):
                raw_count += 1
                if raw_count > MAX_RESULTS:
                    raise TraceProofError("SARIF exceeds the 10,000-result limit")
                rule = result.get("ruleId")
                if not rule and "ruleIndex" in result:
                    rule = indexed(driver["rules"], result["ruleIndex"])["id"]
                if not isinstance(rule, str) or not rule:
                    raise ValueError()
                message = result["message"].get("text", result["message"].get("markdown", ""))
                if not isinstance(message, str):
                    raise ValueError()
                evidence, location_status = None, "unmapped"
                locations = result.get("locations", [])
                if locations:
                    physical = locations[0].get("physicalLocation", {})
                    evidence = bind_location(physical, run, manifest, tree, file_records)
                    if evidence:
                        location_status = "snapshot_bound"
                identity = fingerprint(manifest.snapshot_id, driver, rule, result)
                if identity in seen:
                    continue
                seen.add(identity)
                candidates.append(
                    {
                        "fingerprint": identity,
                        "rule_id": rule,
                        "tool_name": driver.get("name", "unknown"),
                        "tool_version": driver.get(
                            "semanticVersion", driver.get("version", "unknown")
                        ),
                        "message": message,
                        "level": result.get("level", "warning"),
                        "adjudication": "unreviewed",
                        "location_status": location_status,
                        "evidence": evidence,
                        "suppressed": bool(result.get("suppressions")),
                        "code_flow_count": len(result.get("codeFlows", [])),
                    }
                )
        return candidates, {
            "raw_result_count": raw_count,
            "candidate_count": len(candidates),
            "diagnostic_errors": errors,
            "diagnostic_warnings": warnings,
            "execution_complete": bool(complete and errors == 0),
            "unmapped_candidates": sum(item["evidence"] is None for item in candidates),
        }
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, RecursionError):
        raise TraceProofError("Malformed or unsupported SARIF structure") from None
