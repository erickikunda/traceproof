"""Bounded Java syntax inventory; never compiles or executes repository code."""

import json
import resource
import sys

import tree_sitter_java
from tree_sitter import Language, Parser

MAX_BYTES = 1024 * 1024
MAX_NODES = 50_000


def parse(source):
    empty = {"symbols": [], "calls": []}
    if len(source) > MAX_BYTES:
        return {**empty, "status": "size_limit"}
    try:
        source.decode("utf-8")
    except UnicodeDecodeError:
        return {**empty, "status": "encoding_error"}
    root = Parser(Language(tree_sitter_java.language())).parse(source).root_node
    if root.has_error:
        return {**empty, "status": "syntax_error"}
    symbols, calls = [], []
    pending = [(root, "<file>")]
    count = 0
    while pending:
        node, scope = pending.pop()
        count += 1
        if count > MAX_NODES:
            return {**empty, "status": "node_limit"}
        name = node.child_by_field_name("name")
        location = {"line": node.start_point.row + 1, "end_line": node.end_point.row + 1}
        if (
            node.type
            in {
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "record_declaration",
                "annotation_type_declaration",
                "method_declaration",
                "constructor_declaration",
                "compact_constructor_declaration",
            }
            and name is not None
        ):
            scope = f"{scope}.{name.text.decode('utf-8')}"
            symbols.append({"name": scope, "kind": node.type, **location})
        if node.type == "method_invocation" and name is not None:
            calls.append(
                {
                    "expression": name.text.decode("utf-8"),
                    "caller": scope,
                    "resolution": "unresolved",
                    **location,
                }
            )
        pending.extend((child, scope) for child in reversed(node.children))
    return {"status": "parsed", "symbols": symbols, "calls": calls}


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    # macOS does not reliably support RLIMIT_AS; production also needs pod limits.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    print(json.dumps(parse(sys.stdin.buffer.read(MAX_BYTES + 1))))
