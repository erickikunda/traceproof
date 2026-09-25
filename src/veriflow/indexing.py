"""Resumable indexing with atomic publication and read-only report retrieval."""

import hashlib
import json
import subprocess
import sys
from collections import Counter
from uuid import uuid4

from sqlalchemy import select

from veriflow.artifacts import ArtifactStore
from veriflow.domain import VeriFlowError
from veriflow.persistence import IndexedFile, Run, Snapshot, SourceIndex
from veriflow.python_parser import MAX_BYTES

VERSION = (
    f"python-ast-v2-py{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
)


def snapshot_for_run(store, run_id):
    with store.transaction() as session:
        run = session.get(Run, run_id)
        if run is None or run.snapshot_id is None:
            raise VeriFlowError("Run has no captured snapshot")
        snapshot = session.get(Snapshot, run.snapshot_id)
        return run, snapshot


def verified_source(store, run_id):
    run, snapshot = snapshot_for_run(store, run_id)
    artifacts = ArtifactStore(store.root)
    manifest = artifacts.verify(snapshot.id)
    if manifest.model_dump(mode="json") != snapshot.manifest:
        raise VeriFlowError("Snapshot manifest differs from its admitted database record")
    return run, manifest, artifacts.path(snapshot.id) / "tree"


def parse_isolated(source):
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-m", "veriflow.python_parser"],
            input=source,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode:
            return {"status": "parser_failed", "symbols": [], "calls": []}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "symbols": [], "calls": []}


def build_syntax_index(store, run_id):
    """Caller holds exclusive_worker. Completed file checkpoints survive process death."""
    run, manifest, tree = verified_source(store, run_id)
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
        index_id = index.id
        published = index.state == "published"
    if published:
        return coverage_report(store, run_id)
    with store.transaction() as session:
        done = set(
            session.scalars(select(IndexedFile.path).where(IndexedFile.index_id == index_id))
        )
    for record in sorted(manifest.files, key=lambda file: file.path):
        if record.path in done:
            continue
        result = {"status": "not_supported", "symbols": [], "calls": []}
        if record.path.endswith(".py"):
            if record.size_bytes > MAX_BYTES:
                result["status"] = "size_limit"
            else:
                source = (tree / record.path).read_bytes()
                if hashlib.sha256(source).hexdigest() != record.sha256:
                    raise VeriFlowError("Source changed during indexing")
                result = parse_isolated(source)
        result.update(path=record.path, sha256=record.sha256, size_bytes=record.size_bytes)
        with store.transaction() as session:
            session.add(
                IndexedFile(id=str(uuid4()), index_id=index_id, path=record.path, result=result)
            )
    # Detect concurrent local modification before making any index queryable.
    verified_source(store, run_id)
    with store.transaction() as session:
        results = session.scalars(
            select(IndexedFile.result)
            .where(IndexedFile.index_id == index_id)
            .order_by(IndexedFile.path)
        ).yield_per(1)
        counts, file_coverage = Counter(), []
        python_files = functions = calls = 0
        for item in results:
            counts[item["status"]] += 1
            python_files += item["path"].endswith(".py")
            functions += sum(symbol["kind"] == "function" for symbol in item["symbols"])
            calls += len(item["calls"])
            file_coverage.append(
                {key: item[key] for key in ("path", "sha256", "size_bytes", "status")}
            )
        gate = (
            "ready"
            if python_files and counts["parsed"] == python_files and functions
            else "blocked"
        )
        index = session.get(SourceIndex, index_id)
        index.report = {
            "schema_version": "1",
            "report_kind": "index_coverage",
            "index_id": index_id,
            "index_version": VERSION,
            "index_backend": "syntax",
            "snapshot_id": manifest.snapshot_id,
            "classification": manifest.classification,
            "security_analysis_performed": False,
            "security_verdict": "not_assessed",
            "finding_count": None,
            "python_index_gate": gate,
            "total_files": len(file_coverage),
            "python_files": python_files,
            "parsed_python_files": counts["parsed"],
            "python_parse_fraction": counts["parsed"] / python_files if python_files else None,
            "function_count": functions,
            "call_count": calls,
            "unresolved_call_count": calls,
            "files": file_coverage,
            "limitations": [
                "Only .py files are indexed; other files are explicitly not supported.",
                "Calls are unresolved syntax; no interprocedural or taint reachability proof.",
                "The gate checks Python parsing and nonempty function inventory only.",
                "No security queries, LLM analysis, or benchmark evaluation have run.",
            ],
        }
        index.state = "published"
    return coverage_report(store, run_id)


def build_index(store, run_id, backend="syntax", joern_home=None, timeout=300):
    """Build one explicitly selected inventory backend; syntax remains the default."""
    if backend == "syntax":
        return build_syntax_index(store, run_id)
    if backend == "joern":
        from veriflow.joern_indexing import build_index as build_joern_index

        return build_joern_index(store, run_id, joern_home, timeout)
    raise VeriFlowError("Index backend must be syntax or joern")


def published_index(session, snapshot_id, index_id=None):
    index = session.scalar(
        select(SourceIndex).where(
            SourceIndex.snapshot_id == snapshot_id,
            SourceIndex.id == index_id if index_id else SourceIndex.version == VERSION,
            SourceIndex.state == "published",
        )
    )
    if index is None:
        raise VeriFlowError("No published index for this snapshot and parser version")
    return index


def coverage_report(store, run_id, index_id=None):
    run, snapshot = snapshot_for_run(store, run_id)
    with store.transaction() as session:
        index = published_index(session, snapshot.id, index_id)
        return {**index.report, "run_id": run.id, "repo_id": run.repo_id}


def repository_report(store, repo_id, run_id=None, index_id=None):
    with store.transaction() as session:
        query = select(Run).where(Run.repo_id == repo_id)
        if run_id:
            query = query.where(Run.id == run_id)
        run = session.scalar(query.order_by(Run.created_at.desc(), Run.id.desc()).limit(1))
        if run is None:
            raise VeriFlowError("Repository/run not found")
        selected = run.id
    # Latest admitted run is intentional: never silently return an older successful run.
    return coverage_report(store, selected, index_id)


def query_index(store, run_id, kind="symbols", path=None, offset=0, limit=100, index_id=None):
    if kind not in {"symbols", "calls"} or not 1 <= limit <= 1000 or offset < 0:
        raise VeriFlowError("Invalid index query")
    run, snapshot = snapshot_for_run(store, run_id)
    with store.transaction() as session:
        index = published_index(session, snapshot.id, index_id)
        query = select(IndexedFile).where(IndexedFile.index_id == index.id)
        if path is not None:
            query = query.where(IndexedFile.path == path)
        items, total = [], 0
        for file in session.scalars(query.order_by(IndexedFile.path)).yield_per(10):
            for entry in file.result[kind]:
                if offset <= total < offset + limit:
                    items.append(
                        {
                            **entry,
                            "evidence": {
                                "snapshot_id": snapshot.id,
                                "path": file.path,
                                "sha256": file.result["sha256"],
                                "line": entry["line"],
                                "end_line": entry["end_line"],
                            },
                        }
                    )
                total += 1
    return {
        "schema_version": "1",
        "run_id": run.id,
        "kind": kind,
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "index_id": index.id,
    }


def compare_indexes(store, run_id, joern_home, timeout=300):
    """Run both inventories against one snapshot and compare exact normalized records."""
    syntax = build_index(store, run_id, "syntax")
    joern = build_index(store, run_id, "joern", joern_home, timeout)

    def records(index_id, kind):
        result = query_index(store, run_id, kind, limit=1000, index_id=index_id)
        if result["total"] > 1000:
            raise VeriFlowError("Comparison inventory exceeds bounded 1000-record POC limit")
        records = set()
        for item in result["items"]:
            evidence = item["evidence"]
            common = {
                "path": evidence["path"],
                "line": item["line"],
                "end_line": item["end_line"],
            }
            if kind == "symbols":
                record = {
                    **common,
                    "name": item.get("simple_name", item["name"].rsplit(".", 1)[-1]),
                    "kind": item["kind"],
                }
            else:
                record = {
                    **common,
                    "caller": item["caller"].rsplit(".", 1)[-1],
                    "expression": item["expression"],
                }
            records.add(json.dumps(record, sort_keys=True))
        return records

    syntax_symbols = records(syntax["index_id"], "symbols")
    joern_symbols = records(joern["index_id"], "symbols")
    syntax_calls = records(syntax["index_id"], "calls")
    joern_calls = records(joern["index_id"], "calls")
    return {
        "schema_version": "1",
        "report_kind": "index_backend_comparison",
        "run_id": run_id,
        "snapshot_id": syntax["snapshot_id"],
        "baseline": syntax,
        "candidate": joern,
        "comparison": {
            "parsed_python_file_delta": joern["parsed_python_files"]
            - syntax["parsed_python_files"],
            "function_count_delta": joern["function_count"] - syntax["function_count"],
            "call_count_delta": joern["call_count"] - syntax["call_count"],
            "exact_symbol_overlap": len(syntax_symbols & joern_symbols),
            "syntax_only_symbols": len(syntax_symbols - joern_symbols),
            "joern_only_symbols": len(joern_symbols - syntax_symbols),
            "exact_call_overlap": len(syntax_calls & joern_calls),
            "syntax_only_calls": len(syntax_calls - joern_calls),
            "joern_only_calls": len(joern_calls - syntax_calls),
        },
        "interpretation": (
            "Neutral inventory comparison only; count differences are not quality "
            "or security verdicts."
        ),
    }


def report_markdown(report):
    # JSON string quoting keeps metadata single-line; no raw source is included.
    return "\n".join(
        [
            "# TraceProof index coverage report",
            "",
            f"Repository: `{report['repo_id']}`",
            f"Run: `{report['run_id']}`",
            f"Snapshot: `{report['snapshot_id']}`",
            "",
            "**Security verdict: NOT ASSESSED. This is not a vulnerability scan report.**",
            "",
            f"Python index gate: **{report['python_index_gate']}**",
            f"Python files parsed: {report['parsed_python_files']} / {report['python_files']}",
            f"Functions: {report['function_count']}; "
            f"unresolved calls: {report['unresolved_call_count']}",
            "",
            "Limitations:",
            "",
            *[f"- {item}" for item in report["limitations"]],
            "",
            "Per-file coverage is available in the JSON report for dashboard ingestion.",
            "",
        ]
    )
