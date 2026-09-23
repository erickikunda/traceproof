"""Bounded metadata inventory for local retention review; never deletes artifacts."""

import os
import re
import stat

from veriflow.domain import TraceProofError
from veriflow.persistence import CodeqlAttempt, ScanAttempt, Snapshot, exclusive_worker

AREAS = {"artifacts": Snapshot, "codeql": CodeqlAttempt, "scans": ScanAttempt}
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def measure(path, remaining):
    pending = [(path, 0)]
    size = files = nodes = 0
    issues = set()
    while pending:
        if nodes >= remaining:
            issues.add("node_limit")
            break
        current, depth = pending.pop()
        nodes += 1
        try:
            info = current.lstat()
            if stat.S_ISREG(info.st_mode):
                size += info.st_size
                files += 1
            elif stat.S_ISDIR(info.st_mode):
                if depth >= 128:
                    issues.add("depth_limit")
                    continue
                with os.scandir(current) as entries:
                    for entry in entries:
                        if nodes + len(pending) >= remaining:
                            issues.add("node_limit")
                            break
                        pending.append((current / entry.name, depth + 1))
            else:
                issues.add("link_or_special_file_skipped")
        except OSError:
            issues.add("metadata_unavailable")
    return {
        "logical_bytes": size,
        "regular_files": files,
        "visited_nodes": nodes,
        "measurement_complete": not issues,
        "issues": sorted(issues),
    }


def storage_audit(store, max_entries=1000, max_nodes=100000):
    if type(max_entries) is not int or not 1 <= max_entries <= 10000:
        raise TraceProofError("Entry limit must be an integer between 1 and 10000")
    if type(max_nodes) is not int or not 1 <= max_nodes <= 1000000:
        raise TraceProofError("Node limit must be an integer between 1 and 1000000")
    store.require_initialized()
    rows, issues = [], []
    remaining = max_nodes
    # Hold the cooperative worker lock so active publication is not called an orphan.
    with exclusive_worker(store.root), store.transaction() as session:
        for area, model in AREAS.items():
            root = store.root / area
            if root.is_symlink():
                issues.append({"area": area, "issue": "area_link_skipped"})
                continue
            if not root.exists():
                continue
            try:
                with os.scandir(root) as entries:
                    for entry in entries:
                        if len(rows) >= max_entries:
                            issues.append({"area": area, "issue": "entry_limit"})
                            break
                        name = entry.name
                        identity = (
                            bool(re.fullmatch(r"[0-9a-f]{64}", name))
                            if area == "artifacts"
                            else bool(UUID.fullmatch(name))
                        )
                        referenced = session.get(model, name) is not None if identity else False
                        kind = (
                            "referenced"
                            if referenced
                            else "unreferenced"
                            if identity
                            else "staging"
                            if area == "artifacts" and name.startswith(".stage-")
                            else "unrecognized"
                        )
                        summary = measure(root / name, remaining)
                        if not entry.is_dir(follow_symlinks=False):
                            summary["measurement_complete"] = False
                            summary["issues"].append("artifact_directory_expected")
                        remaining -= summary["visited_nodes"]
                        rows.append(
                            {"area": area, "entry": name, "reference_status": kind, **summary}
                        )
            except OSError:
                issues.append({"area": area, "issue": "area_unavailable"})
    rows.sort(key=lambda row: (row["area"], row["entry"]))
    return {
        "schema_version": "1",
        "status": "incomplete"
        if issues or any(not row["measurement_complete"] for row in rows)
        else "inventory_complete",
        "max_entries": max_entries,
        "max_nodes": max_nodes,
        "items": rows,
        "issues": issues,
        "observed_logical_bytes": sum(row["logical_bytes"] for row in rows),
        "visited_nodes": max_nodes - remaining,
        "scope": "Present artifacts only; no deletion, integrity check or missing-record audit",
        "limitations": [
            "Logical sizes are not allocated disk usage; hard links may be counted repeatedly.",
            "Database, WAL, backups and other state directories are excluded.",
            "Unreferenced/staging entries require operator investigation, not automatic deletion.",
            "The worker lock coordinates TraceProof, not external filesystem changes.",
            "Truncated selection follows filesystem enumeration order and is not a resumable page.",
        ],
    }
