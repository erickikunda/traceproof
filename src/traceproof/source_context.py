"""Complete bounded source reconstruction from consistent evidence excerpts."""

import io


def complete_context(bundle, snippet, suffix=".java"):
    """Join only consistent, snapshot-bound excerpts; never fill unseen lines."""
    if not snippet.get("path", "").endswith(suffix):
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
