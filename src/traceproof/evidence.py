"""Bounded, integrity-checked source evidence. Source is data, never instructions."""

import hashlib
import io
import tokenize

from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.python_parser import MAX_BYTES


def source_evidence(store, run_id, path, line, end_line, sha256=None):
    if line < 1 or end_line < line or end_line - line + 1 > 200:
        raise TraceProofError("Evidence requires an inclusive range of 1–200 lines")
    _, manifest, tree = verified_source(store, run_id)
    record = next((item for item in manifest.files if item.path == path), None)
    if record is None or record.size_bytes > MAX_BYTES:
        raise TraceProofError("Evidence file is absent or exceeds the 1 MiB read limit")
    if sha256 is not None and record.sha256 != sha256:
        raise TraceProofError("Evidence digest does not match the snapshot")
    with (tree / record.path).open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if hashlib.sha256(raw).hexdigest() != record.sha256:
        raise TraceProofError("Evidence source changed")
    try:
        encoding = tokenize.detect_encoding(io.BytesIO(raw).readline)[0]
        lines = raw.decode(encoding).splitlines(keepends=True)
    except (SyntaxError, UnicodeError, LookupError):
        raise TraceProofError("Evidence encoding is unsupported") from None
    if end_line > len(lines):
        raise TraceProofError("Evidence range exceeds the file")
    text = "".join(lines[line - 1 : end_line])
    if len(text.encode("utf-8")) > 32 * 1024:
        raise TraceProofError("Evidence exceeds the 32 KiB response limit; request fewer lines")
    return {
        "schema_version": "1",
        "run_id": run_id,
        "snapshot_id": manifest.snapshot_id,
        "path": path,
        "sha256": record.sha256,
        "line": line,
        "end_line": end_line,
        "classification": manifest.classification,
        "trust": "untrusted_source",
        "text": text,
    }
