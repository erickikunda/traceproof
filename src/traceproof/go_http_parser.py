"""Bounded Go HTTP and shell syntax endpoints; never builds or executes source."""

import json
import os
import resource
import subprocess
import sys
from collections import Counter
from pathlib import Path

import tree_sitter_go
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
    root = Parser(Language(tree_sitter_go.language())).parse(source).root_node
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
            if n.type == "identifier"
            and node.start_byte <= n.start_byte
            and n.end_byte <= node.end_byte
        ]

    imports, bindings, writes = {}, Counter(), set()
    for node in nodes:
        if node.type == "import_spec":
            name = text(field(node, "name"))
            if name == ".":
                return {**empty, "status": "dot_import"}
            path = text(field(node, "path"))
            if path.startswith('"'):
                try:
                    package = json.loads(path)
                except ValueError:
                    return {**empty, "status": "unsupported_import"}
                name = name or package.rsplit("/", 1)[-1]
                bindings[name] += 1
                imports[name] = package
            else:
                return {**empty, "status": "unsupported_import"}
        elif node.type in {
            "parameter_declaration",
            "variadic_parameter_declaration",
            "var_spec",
            "const_spec",
            "type_spec",
            "type_alias",
            "function_declaration",
            "method_declaration",
        }:
            for name in node.children_by_field_name("name"):
                bindings[text(name)] += 1
        elif node.type == "short_var_declaration":
            bindings.update(identifiers(field(node, "left")))
        elif node.type in {"assignment_statement", "range_clause", "receive_statement"}:
            writes.update(identifiers(field(node, "left")))
        elif node.type in {"inc_statement", "dec_statement"}:
            writes.update(identifiers(node))
    trusted = {
        name: path
        for name, path in imports.items()
        if bindings[name] == 1 and name not in writes and name != "_"
    }
    receivers = []
    for function in nodes:
        if function.type != "function_declaration":
            continue
        params, body = field(function, "parameters"), field(function, "body")
        if not params or not body:
            continue
        for param in params.named_children:
            kind = field(param, "type")
            if not kind or kind.type != "pointer_type" or len(kind.named_children) != 1:
                continue
            kind = kind.named_children[0]
            if (
                kind.type != "qualified_type"
                or text(field(kind, "name")) != "Request"
                or trusted.get(text(field(kind, "package"))) != "net/http"
            ):
                continue
            for name in param.children_by_field_name("name"):
                if bindings[text(name)] == 1 and text(name) not in writes:
                    receivers.append((text(name), body.start_byte, body.end_byte))
    sources, sinks = [], []
    for node in nodes:
        if node.type != "call_expression" or node.start_point.row != node.end_point.row:
            continue
        func, args = field(node, "function"), field(node, "arguments")
        if not func or func.type != "selector_expression" or not args:
            continue
        receiver, method = field(func, "operand"), text(field(func, "field"))
        if not receiver or receiver.type != "identifier":
            continue
        arguments = args.named_children
        location = {"line": node.start_point.row + 1, "code": text(node)}
        if (
            method in {"FormValue", "PostFormValue"}
            and len(arguments) == 1
            and arguments[0].type == "interpreted_string_literal"
            and any(
                text(receiver) == name and start <= node.start_byte < node.end_byte <= end
                for name, start, end in receivers
            )
        ):
            sources.append(location)
        if (
            trusted.get(text(receiver)) == "os/exec"
            and method == "Command"
            and len(arguments) == 3
            and text(arguments[0]) in {'"sh"', '"bash"', '"/bin/sh"', '"/bin/bash"'}
            and text(arguments[1]) == '"-c"'
            and arguments[2].type != "variadic_argument"
        ):
            sinks.append({**location, "argument_code": text(arguments[2])})
    return {"status": "parsed", "sources": sources, "sinks": sinks}


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
