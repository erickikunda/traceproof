"""Bounded observations of pinned Joern logs, never an authoritative parser inventory."""

import hashlib
import re

LIMIT = 1024 * 1024
ANSI = re.compile(r"\x1b\[[0-9;]*m")
EVENT = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+\s+(WARN|ERROR)\s+(\S+)\s+(.*)$")
PROBLEM = re.compile(r"(?:Encountered problems while parsing|Failed to process) '([^']+)'")


def observe_logs(root, selected):
    known = {record.path for record in selected}
    stages = {}
    for name in ("prepare", "analyze"):
        try:
            with (root / f"{name}.log").open("rb") as handle:
                raw = handle.read(LIMIT + 1)
        except OSError:
            stages[name] = {"state": "unavailable"}
            continue
        truncated = len(raw) > LIMIT
        raw = raw[:LIMIT]
        warnings = errors = unknown_paths = 0
        affected = set()
        for line in raw.decode("utf-8", errors="replace").splitlines():
            event = EVENT.match(ANSI.sub("", line))
            if not event:
                continue
            level, logger, message = event.groups()
            warnings += level == "WARN"
            errors += level == "ERROR"
            if logger in {"SourceParser", "AstCreationPass"}:
                problem = PROBLEM.search(message)
                if problem:
                    path = problem.group(1)
                    if path in known:
                        affected.add(path)
                    else:
                        unknown_paths += 1
        stages[name] = {
            "state": "truncated" if truncated else "observed",
            "inspected_bytes": len(raw),
            "inspected_prefix_sha256": hashlib.sha256(raw).hexdigest(),
            "warning_events": warnings,
            "error_events": errors,
            "parser_problem_files": sorted(affected),
            "unmapped_parser_events": unknown_paths,
        }
    return {
        "schema_version": "1",
        "joern_version": "4.0.625",
        "stages": stages,
        "authoritative": False,
        "parse_completeness_verified": False,
        "scope": "Recognized log events only; absence is not proof of successful parsing",
    }
