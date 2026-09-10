"""Snapshot-bound Java syntax checkpoints, separate from semantic qualification."""

import hashlib
import json
import subprocess
import sys
from importlib.metadata import version
from uuid import uuid4

from sqlalchemy import select

from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.java_parser import MAX_BYTES
from traceproof.persistence import IndexedFile, SourceIndex

VERSION = f"java-syntax-v1-ts{version('tree-sitter')}-java{version('tree-sitter-java')}"


def parse_isolated(source):
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-m", "traceproof.java_parser"],
            input=source,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "symbols": [], "calls": []}
    return {"status": "parser_failed", "symbols": [], "calls": []}


def build_java_index(store, run_id):
    """Caller holds the worker lock. Publish only after source re-verification."""
    _, manifest, tree = verified_source(store, run_id)
    with store.transaction() as session:
        index = session.scalar(
            select(SourceIndex).where(
                SourceIndex.snapshot_id == manifest.snapshot_id, SourceIndex.version == VERSION
            )
        )
        if index is None:
            index = SourceIndex(
                id=str(uuid4()), snapshot_id=manifest.snapshot_id, version=VERSION, state="building"
            )
            session.add(index)
        if index.state == "published":
            return index.report
        index_id = index.id
        done = set(
            session.scalars(select(IndexedFile.path).where(IndexedFile.index_id == index_id))
        )
    for file in manifest.files:
        if not file.path.lower().endswith(".java") or file.path in done:
            continue
        result = {"status": "size_limit", "symbols": [], "calls": []}
        if file.size_bytes <= MAX_BYTES:
            source = (tree / file.path).read_bytes()
            if hashlib.sha256(source).hexdigest() != file.sha256:
                raise TraceProofError("Source changed during Java indexing")
            result = parse_isolated(source)
        with store.transaction() as session:
            session.add(
                IndexedFile(
                    id=str(uuid4()),
                    index_id=index_id,
                    path=file.path,
                    result={**result, "path": file.path, "sha256": file.sha256},
                )
            )
    verified_source(store, run_id)
    with store.transaction() as session:
        rows = list(
            session.scalars(
                select(IndexedFile.result)
                .where(IndexedFile.index_id == index_id)
                .order_by(IndexedFile.path)
            )
        )
        report = {
            "version": "1",
            "index_id": index_id,
            "index_version": VERSION,
            "snapshot_id": manifest.snapshot_id,
            "language": "java",
            "java_files": len(rows),
            "parsed_java_files": sum(r["status"] == "parsed" for r in rows),
            "symbol_count": sum(len(r["symbols"]) for r in rows),
            "unresolved_call_count": sum(len(r["calls"]) for r in rows),
            "syntax_gate": "ready"
            if rows and all(r["status"] == "parsed" for r in rows)
            else "blocked",
            "files": [{k: r[k] for k in ("path", "sha256", "status")} for r in rows],
            "semantic_resolution": "not_qualified",
            "security_completion_verified": False,
        }
        index = session.get(SourceIndex, index_id)
        index.report, index.state = report, "published"
    return report
