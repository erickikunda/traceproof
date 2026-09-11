"""Bounded Rust environment/shell syntax; no compilation or macro expansion."""

import json
import os
import resource
import subprocess
import sys
from collections import Counter
from pathlib import Path

import tree_sitter_rust
from tree_sitter import Language, Parser

MAX_BYTES = 1024 * 1024
MAX_NODES = 50_000


def parse(source):
    empty = {"sources": [], "sinks": []}
    if len(source) > MAX_BYTES:
        return {**empty, "status": "size_limit"}
    try:
        source.decode("utf-8")
    except UnicodeError:
        return {**empty, "status": "encoding_error"}
    root = Parser(Language(tree_sitter_rust.language())).parse(source).root_node
    if root.has_error:
        return {**empty, "status": "syntax_error"}
    nodes, pending = [], [root]
    while pending:
        node = pending.pop()
        nodes.append(node)
        if len(nodes) > MAX_NODES:
            return {**empty, "status": "node_limit"}
        pending.extend(reversed(node.named_children))

    def field(node, key):
        return node.child_by_field_name(key) if node else None

    def text(node):
        return node.text.decode() if node else ""

    def identifiers(node):
        if node is None:
            return []
        return [
            text(n)
            for n in nodes
            if n.type in {"identifier", "type_identifier"}
            and node.start_byte <= n.start_byte
            and n.end_byte <= node.end_byte
        ]

    bindings, aliases = Counter(), {}
    for node in nodes:
        if node.type in {
            "macro_definition",
            "macro_invocation",
            "attribute_item",
            "inner_attribute_item",
            "extern_crate_declaration",
        }:
            return {**empty, "status": "unsupported_context"}
        if node.type == "use_declaration":
            arg = field(node, "argument")
            if (
                node.parent != root
                or not arg
                or arg.type not in {"scoped_identifier", "use_as_clause"}
            ):
                return {**empty, "status": "unsupported_import"}
            path = field(arg, "path") if arg.type == "use_as_clause" else arg
            name = (
                text(field(arg, "alias"))
                if arg.type == "use_as_clause"
                else text(field(arg, "name"))
            )
            if not name or name == "_":
                return {**empty, "status": "unsupported_import"}
            bindings[name] += 1
            aliases[name] = text(path)
        elif node.type in {
            "function_item",
            "mod_item",
            "struct_item",
            "enum_item",
            "type_item",
            "trait_item",
            "const_item",
            "static_item",
            "type_parameter",
        }:
            bindings.update(identifiers(field(node, "name")))
        elif node.type in {"let_declaration", "parameter", "for_expression", "match_arm"}:
            bindings.update(identifiers(field(node, "pattern")))
        elif node.type in {"assignment_expression", "compound_assignment_expr"}:
            bindings.update(identifiers(field(node, "left")))
    # A local std binding makes even written std:: paths ambiguous for this bounded gate.
    if bindings["std"]:
        return {**empty, "status": "shadowed_std"}
    sources = {"std::env::var"}
    constructors = {"std::process::Command::new"}
    for name, path in aliases.items():
        if bindings[name] != 1:
            continue
        if path == "std::env::var":
            sources.add(name)
        if path == "std::process::Command":
            constructors.add(name + "::new")

    def call(node):
        if not node or node.type != "call_expression":
            return None, []
        arguments = field(node, "arguments")
        return field(node, "function"), arguments.named_children if arguments else []

    source_nodes, sinks = [], []
    for node in nodes:
        if node.type != "call_expression" or node.start_point.row != node.end_point.row:
            continue
        func, args = call(node)
        if text(func) in sources and len(args) == 1 and args[0].type == "string_literal":
            source_nodes.append({"line": node.start_point.row + 1, "code": text(node)})
        if (
            not func
            or func.type != "field_expression"
            or text(field(func, "field")) != "arg"
            or len(args) != 1
        ):
            continue
        flag, flag_args = call(field(func, "value"))
        if (
            not flag
            or flag.type != "field_expression"
            or text(field(flag, "field")) != "arg"
            or len(flag_args) != 1
            or text(flag_args[0]) != '"-c"'
        ):
            continue
        constructor, shell_args = call(field(flag, "value"))
        if (
            text(constructor) in constructors
            and len(shell_args) == 1
            and text(shell_args[0]) in {'"sh"', '"bash"', '"/bin/sh"', '"/bin/bash"'}
        ):
            sinks.append(
                {
                    "line": node.start_point.row + 1,
                    "code": text(node),
                    "argument_code": text(args[0]),
                }
            )
    return {"status": "parsed", "sources": source_nodes, "sinks": sinks}


def parse_isolated(source):
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve())],
            input=source,
            capture_output=True,
            timeout=10,
            env={"PATH": os.defpath},
        )
        if result.returncode:
            raise ValueError()
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return {"status": "parser_failed", "sources": [], "sinks": []}


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    print(json.dumps(parse(sys.stdin.buffer.read(MAX_BYTES + 1))))
