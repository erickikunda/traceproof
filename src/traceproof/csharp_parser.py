"""Bounded C# syntax anchors for advisory review; no symbol binding proof."""

import json
import resource
import sys

import tree_sitter_c_sharp
from tree_sitter import Language, Parser

MAX_BYTES = 16 * 1024
MAX_NODES = 50_000


def parse(source):
    empty = {"sources": [], "sinks": []}
    if len(source) > MAX_BYTES:
        return {**empty, "status": "size_limit"}
    try:
        source.decode("utf-8")
    except UnicodeDecodeError:
        return {**empty, "status": "encoding_error"}
    root = Parser(Language(tree_sitter_c_sharp.language())).parse(source).root_node
    if root.has_error:
        return {**empty, "status": "syntax_error"}
    nodes, pending = [], [root]
    while pending:
        node = pending.pop()
        nodes.append(node)
        if len(nodes) > MAX_NODES:
            return {**empty, "status": "node_limit"}
        pending.extend(node.children)
    # Aliases, conditional compilation and local attribute lookalikes are not qualified.
    if any(n.type.startswith("preproc_") for n in nodes):
        return {**empty, "status": "unsupported_context"}
    for node in nodes:
        if node.type.endswith("_declaration"):
            name = node.child_by_field_name("name")
            if name and name.text.decode() in {"FromQuery", "FromQueryAttribute"}:
                return {**empty, "status": "unsupported_context"}
    imports = [n.text.decode().strip() for n in nodes if n.type == "using_directive"]
    allowed = {"using Microsoft.AspNetCore.Mvc;", "using Microsoft.AspNetCore.Builder;"}
    if any(
        i not in allowed and not (i.startswith("using System.") and "=" not in i) for i in imports
    ):
        return {**empty, "status": "unsupported_context"}
    sources, sinks = [], []
    for node in nodes:
        location = dict(line=node.start_point.row + 1, end_line=node.end_point.row + 1)
        if node.type == "attribute":
            name = node.child_by_field_name("name")
            written = name.text.decode() if name else ""
            target = node.parent.parent if node.parent else None
            if (
                target
                and target.type == "parameter"
                and (
                    written
                    in {
                        "Microsoft.AspNetCore.Mvc.FromQuery",
                        "Microsoft.AspNetCore.Mvc.FromQueryAttribute",
                    }
                    or written in {"FromQuery", "FromQueryAttribute"}
                    and "using Microsoft.AspNetCore.Mvc;" in imports
                )
            ):
                sources.append(location)
        if node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            name = left.child_by_field_name("name") if left else None
            if (
                left
                and left.type == "member_access_expression"
                and name is not None
                and name.text == b"CommandText"
            ):
                sinks.append(location)
    return dict(status="parsed", sources=sources, sinks=sinks)


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    print(json.dumps(parse(sys.stdin.buffer.read(MAX_BYTES + 1))))
