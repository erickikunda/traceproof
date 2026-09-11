"""Experimental C# syntax-span validation; never a flow or identity qualification."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

VERSION = "joern-csharp-span-2"
MAX_SOURCE_BYTES = 16 * 1024
MAX_REQUEST_BYTES = 256 * 1024
MAX_GRAPH_NODES = 256


def validate_locations(
    source: bytes, expected_sha256: str, nodes: list[dict], *, framework_facts: bool = False
) -> dict:
    """Parse untrusted source only in a bounded child process; no file paths from nodes."""
    if len(source) > MAX_SOURCE_BYTES or len(nodes) > MAX_GRAPH_NODES:
        return {"version": VERSION, "status": "limit", "nodes": []}
    try:
        payload = json.dumps(
            {
                "source": source.decode("utf-8"),
                "sha256": expected_sha256,
                "nodes": nodes,
                "framework_facts": framework_facts,
            }
        ).encode()
    except (UnicodeDecodeError, TypeError):
        return {"version": VERSION, "status": "invalid_input", "nodes": []}
    if len(payload) > MAX_REQUEST_BYTES:
        return {"version": VERSION, "status": "limit", "nodes": []}
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve())],
            input=payload,
            capture_output=True,
            timeout=10,
            check=True,
            env={"PATH": os.defpath},
        )
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, ValueError):
        return {"version": VERSION, "status": "parser_failed", "nodes": []}


def map_spans(request: dict) -> dict:
    """Child implementation. Exact named syntax spans only; no whitespace rewriting."""
    import tree_sitter_c_sharp
    from tree_sitter import Language, Parser

    source = request["source"].encode("utf-8")
    nodes = request["nodes"]
    base = {"version": VERSION, "status": "unsupported", "nodes": []}
    if len(source) > MAX_SOURCE_BYTES or len(nodes) > MAX_GRAPH_NODES:
        return {**base, "status": "limit"}
    digest = hashlib.sha256(source).hexdigest()
    if digest != request["sha256"]:
        return {**base, "status": "source_mismatch"}
    tree = Parser(Language(tree_sitter_c_sharp.language())).parse(source)
    if tree.root_node.has_error:
        return {**base, "status": "syntax_error"}
    spans = []
    stack = [tree.root_node]
    count = 0
    allowed = {
        "parameter",
        "identifier",
        "binary_expression",
        "invocation_expression",
        "member_access_expression",
        "assignment_expression",
        "argument",
    }
    while stack:
        node = stack.pop()
        count += 1
        if count > 50_000:
            return {**base, "status": "limit"}
        # Never accept identifiers inside comments, strings, or attributes as flow anchors.
        if "string" in node.type or node.type in {"comment", "attribute_list"}:
            continue
        if node.type in allowed:
            spans.append(node)
        if node.type == "parameter":
            # Joern may omit parameter attributes from its code property.
            from types import SimpleNamespace

            kind = node.child_by_field_name("type")
            name = node.child_by_field_name("name")
            if kind and name and kind.start_byte != node.start_byte:
                spans.append(
                    SimpleNamespace(
                        start_byte=kind.start_byte,
                        end_byte=name.end_byte,
                        start_point=kind.start_point,
                        end_point=name.end_point,
                        text=source[kind.start_byte : name.end_byte],
                        type="parameter_type_and_name",
                    )
                )
        stack.extend(node.named_children)
    facts = {"status": "not_requested", "sources": [], "sinks": []}
    if request.get("framework_facts"):
        # Load only the trusted sibling parser, also within this isolated child.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "trusted_csharp_parser", Path(__file__).with_name("csharp_parser.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        facts = module.parse(source, include_spans=True)
    results = []
    for raw in nodes:
        line, code = raw.get("line"), raw.get("code")
        result = {"raw": raw, "status": "unsupported", "span": None}
        if type(line) is not int or line < 0 or not isinstance(code, str) or not code:
            results.append(result)
            continue
        # The pinned frontend exhibits both direct and preceding-line coordinates.
        # Evaluate both, accepting neither if more than one distinct span fits.
        candidates = {
            (n.start_byte, n.end_byte): n
            for n in spans
            if n.start_point.row + 1 in {line, line + 1} and n.text == code.encode()
        }
        if len(candidates) == 1:
            node = next(iter(candidates.values()))
            result.update(
                status="validated_span",
                span={
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                    "line": node.start_point.row + 1,
                    "end_line": node.end_point.row + 1,
                    "syntax_kind": node.type,
                    "sha256": digest,
                    "line_delta": node.start_point.row + 1 - line,
                },
            )
        elif candidates:
            result["status"] = "ambiguous"
        if request.get("framework_facts"):
            result["framework_facts"] = []
            span = result["span"]
            if span and facts["status"] == "parsed":
                for category in ("sources", "sinks"):
                    for fact in facts[category]:
                        if (
                            fact["start_byte"] <= span["start_byte"]
                            and span["end_byte"] <= fact["end_byte"]
                        ):
                            result["framework_facts"].append(
                                {
                                    **fact,
                                    "category": category,
                                    "sha256": digest,
                                    "qualification": "syntax_only",
                                }
                            )
        results.append(result)
    return {
        "version": VERSION,
        "status": "parsed",
        "nodes": results,
        "framework_status": facts["status"],
    }


if __name__ == "__main__":
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    payload = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if len(payload) > MAX_REQUEST_BYTES:
        print(json.dumps({"version": VERSION, "status": "limit", "nodes": []}))
    else:
        print(json.dumps(map_spans(json.loads(payload))))
