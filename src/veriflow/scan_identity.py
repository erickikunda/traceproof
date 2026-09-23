"""Recorded analysis identity; an entry-file hash is not a reusable rule-pack pin."""

import hashlib
import json


def analysis_identity(report):
    configuration = {
        "schema_version": "1",
        "scanner": report["scanner"],
        "snapshot_id": report["snapshot_id"],
        "language": report["language"],
        "language_scope": report.get("language_scope"),
        "preparation_tool_version": report["prepared_input"]["tool_version"],
        "input_kind": report["prepared_input"]["kind"],
        "rule_entry": report["rule_entry"],
        "requested_resources": report["requested_resources"],
        "timeout_seconds": report["timeout_seconds"],
    }
    digest = hashlib.sha256(
        json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": "1",
        "configuration_sha256": digest,
        "automatic_reuse_eligible": False,
        "reason": "Transitive rule packs and prepared artifact contents are not pinned",
    }
