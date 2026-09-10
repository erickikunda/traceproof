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
    symbols, calls, annotations = [], [], []
    imports = {}
    for child in root.named_children:
        if child.type == "import_declaration":
            names = [
                n for n in child.named_children if n.type in {"identifier", "scoped_identifier"}
            ]
            if names and not any(n.type in {"asterisk", "static"} for n in child.children):
                qualified = names[0].text.decode("utf-8")
                imports.setdefault(qualified.rsplit(".", 1)[-1], []).append(qualified)
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
        if node.type in {"annotation", "marker_annotation"} and name is not None:
            written = name.text.decode("utf-8")
            candidates = imports.get(written, [])
            qualified = (
                written if "." in written else candidates[0] if len(candidates) == 1 else None
            )
            target = node.parent
            if target and target.type == "modifiers":
                target = target.parent
            target_name = target.child_by_field_name("name") if target else None
            annotations.append(
                {
                    "name": written,
                    "qualified_name_hint": qualified,
                    "name_evidence": "qualified_syntax"
                    if "." in written
                    else "explicit_import"
                    if len(candidates) == 1
                    else "unresolved",
                    "scope": scope,
                    "target_kind": target.type if target else None,
                    "target_name": target_name.text.decode("utf-8") if target_name else None,
                    "binding_proven": False,
                    **location,
                }
            )
        pending.extend((child, scope) for child in reversed(node.children))
    return {"status": "parsed", "symbols": symbols, "calls": calls, "annotations": annotations}


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    # macOS does not reliably support RLIMIT_AS; production also needs pod limits.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    print(json.dumps(parse(sys.stdin.buffer.read(MAX_BYTES + 1))))
