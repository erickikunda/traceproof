"""Narrow Java SQL syntax anchors; no binding or exploitability proof."""

import io

from traceproof.java_index import parse_isolated


def complete_context(bundle, snippet):
    """Join only consistent, snapshot-bound excerpts; never fill unseen lines."""
    if not snippet.get("path", "").endswith(".java"):
        return None
    pieces = [
        s
        for s in bundle["snippets"]
        if s["path"] == snippet["path"]
        and s["sha256"] == snippet["sha256"]
        and s.get("snapshot_id") == snippet.get("snapshot_id")
    ]
    totals = {s["source_line_count"] for s in pieces if "source_line_count" in s}
    if len(totals) != 1:
        return None
    total = totals.pop()
    if not isinstance(total, int) or not 1 <= total <= 16384:
        return None
    lines = {}
    for piece in pieces:
        text = io.StringIO(piece["text"], newline="").readlines()
        start, end = piece["excerpt_line"], piece["excerpt_end_line"]
        if not 1 <= start <= end <= total or len(text) != end - start + 1:
            return None
        for number, line in enumerate(text, start):
            if number in lines and lines[number] != line:
                return None
            lines[number] = line
    if set(lines) != set(range(1, total + 1)):
        return None
    source = "".join(lines[number] for number in range(1, total + 1))
    if len(source.encode("utf-8")) > 16 * 1024:
        return None
    return source


def anchors(bundle, snippet, claim):
    source = complete_context(bundle, snippet)
    if source is None:
        return []
    parsed = parse_isolated(source.encode("utf-8"))
    if parsed["status"] != "parsed":
        return []
    lines = io.StringIO(source, newline="").readlines()
    facts = []
    if claim.obligation == "source":
        if any(s["name"].rsplit(".", 1)[-1] == "RequestParam" for s in parsed["symbols"]):
            return []
        facts = [
            a
            for a in parsed.get("annotations", [])
            if a["qualified_name_hint"] == "org.springframework.web.bind.annotation.RequestParam"
            and a["target_kind"] == "formal_parameter"
        ]
    elif claim.obligation == "sink":
        facts = [c for c in parsed["calls"] if c["expression"] == "executeQuery"]
    # Guards and counterevidence deliberately have no qualified Java vocabulary yet.
    return [
        (f["line"], f["end_line"])
        for f in facts
        if claim.line <= f["line"] <= f["end_line"] <= claim.end_line
        and "".join(lines[f["line"] - 1 : f["end_line"]]).strip() in claim.quote
    ]
