"""Narrow Java SQL syntax anchors; no binding or exploitability proof."""

import io

from traceproof.java_index import parse_isolated


def anchors(snippet, claim):
    # Fragment parsing could hide foreign imports or local annotation definitions.
    if snippet.get("excerpt_line") != 1 or snippet.get("excerpt_end_line") != snippet.get(
        "source_line_count"
    ):
        return []
    if not snippet.get("path", "").endswith(".java"):
        return []
    if len(io.StringIO(snippet["text"], newline="").readlines()) != snippet["source_line_count"]:
        return []
    parsed = parse_isolated(snippet["text"].encode("utf-8"))
    if parsed["status"] != "parsed":
        return []
    lines = io.StringIO(snippet["text"], newline="").readlines()
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
