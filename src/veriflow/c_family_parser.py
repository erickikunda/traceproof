"""Bounded C-style argv/system syntax; no preprocessing, compilation or execution."""

import json
import os
import re
import resource
import subprocess
import sys
from collections import Counter
from pathlib import Path

from tree_sitter import Language, Parser

MAX_BYTES = 1024 * 1024
MAX_NODES = 50_000


def parse(source, language):
    empty = {"sources": [], "sinks": []}
    if len(source) > MAX_BYTES:
        return {**empty, "status": "size_limit"}
    try:
        source.decode("utf-8")
    except UnicodeError:
        return {**empty, "status": "encoding_error"}
    if language == "c":
        import tree_sitter_c

        grammar = tree_sitter_c.language()
    elif language == "cpp":
        import tree_sitter_cpp

        grammar = tree_sitter_cpp.language()
    else:
        return {**empty, "status": "unsupported_language"}
    root = Parser(Language(grammar)).parse(source).root_node
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

    def declaration(node):
        chain = []
        while node is not None:
            chain.append(node.type)
            if node.type == "identifier":
                return text(node), chain
            if node.type == "array_declarator" and field(node, "size") is not None:
                return "", chain
            node = field(node, "declarator")
        return "", chain

    bindings, writes, includes = Counter(), set(), set()
    for node in nodes:
        if node.type.startswith("preproc_") and node.type != "preproc_include":
            return {**empty, "status": "unsupported_preprocessing"}
        if node.type in {
            "namespace_definition",
            "class_specifier",
            "template_declaration",
            "lambda_expression",
        }:
            return {**empty, "status": "unsupported_cpp_context"}
        if node.type == "preproc_include":
            includes.add(text(field(node, "path")))
        if node.type in {
            "declaration",
            "parameter_declaration",
            "function_definition",
            "field_declaration",
            "type_definition",
        }:
            for declarator in node.children_by_field_name("declarator"):
                name, _ = declaration(declarator)
                if name:
                    bindings[name] += 1
        if node.type in {"assignment_expression", "update_expression"}:
            target = field(node, "left") or field(node, "argument")
            if target:
                writes.update(
                    text(n)
                    for n in nodes
                    if n.type == "identifier"
                    and target.start_byte <= n.start_byte
                    and n.end_byte <= target.end_byte
                )
    argv = []
    for function in root.named_children:
        if function.type != "function_definition" or text(field(function, "type")) != "int":
            continue
        declarator = field(function, "declarator")
        name, chain = declaration(declarator)
        if name != "main" or chain != ["function_declarator", "identifier"] or bindings[name] != 1:
            continue
        params = field(declarator, "parameters")
        params = params.named_children if params else []
        if (
            len(params) != 2
            or text(field(params[0], "type")) != "int"
            or text(field(params[1], "type")) != "char"
        ):
            continue
        parameter = params[1]
        name, shape = declaration(field(parameter, "declarator"))
        if shape not in [
            ["pointer_declarator", "pointer_declarator", "identifier"],
            ["pointer_declarator", "array_declarator", "identifier"],
        ]:
            continue
        if (
            any(n.type == "type_qualifier" for n in parameter.named_children)
            or bindings[name] != 1
            or name in writes
        ):
            continue
        body = field(function, "body")
        if body:
            argv.append((name, body.start_byte, body.end_byte))
    sources, sinks = [], []
    for node in nodes:
        if node.start_point.row != node.end_point.row:
            continue
        if node.type == "subscript_expression":
            receiver = field(node, "argument")
            index = field(node, "index")
            if language == "cpp":
                indices = field(node, "indices")
                index = (
                    indices.named_children[0]
                    if indices and len(indices.named_children) == 1
                    else None
                )
            if (
                receiver
                and receiver.type == "identifier"
                and index
                and index.type == "number_literal"
                and re.fullmatch(r"[1-9][0-9]*", text(index))
                and any(
                    text(receiver) == name and start <= node.start_byte < node.end_byte <= end
                    for name, start, end in argv
                )
            ):
                sources.append({"line": node.start_point.row + 1, "code": text(node)})
        if (
            node.type == "call_expression"
            and not bindings["system"]
            and "system" not in writes
            and "<stdlib.h>" in includes
        ):
            func, arguments = field(node, "function"), field(node, "arguments")
            args = arguments.named_children if arguments else []
            if func and func.type == "identifier" and text(func) == "system" and len(args) == 1:
                sinks.append(
                    {
                        "line": node.start_point.row + 1,
                        "code": text(node),
                        "argument_code": text(args[0]),
                    }
                )
    return {"status": "parsed", "sources": sources, "sinks": sinks}


def parse_isolated(source, language):
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve()), language],
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
    print(json.dumps(parse(sys.stdin.buffer.read(MAX_BYTES + 1), sys.argv[1])))
