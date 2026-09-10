"""Narrow ASP.NET Core SQL syntax checks; never a safety or reachability proof."""

import io
import json
import subprocess
import sys

from traceproof.source_context import complete_context


def anchors(bundle, snippet, claim):
    source = complete_context(bundle, snippet, suffix=".cs")
    if source is None or claim.obligation not in ("source", "sink"):
        return []
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-m", "traceproof.csharp_parser"],
            input=source.encode(),
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode:
            return []
        parsed = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return []
    if parsed["status"] != "parsed":
        return []
    lines = io.StringIO(source, newline="").readlines()
    return [
        (fact["line"], fact["end_line"])
        for fact in parsed[claim.obligation + "s"]
        if claim.line <= fact["line"] <= fact["end_line"] <= claim.end_line
        and "".join(lines[fact["line"] - 1 : fact["end_line"]]).strip() in claim.quote
    ]
