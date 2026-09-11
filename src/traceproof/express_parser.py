"""Bounded Express syntax endpoints; repository code is never imported or executed."""

import json
import os
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
    if language == "javascript":
        import tree_sitter_javascript

        grammar = tree_sitter_javascript.language()
    elif language == "typescript":
        import tree_sitter_typescript

        grammar = tree_sitter_typescript.language_typescript()
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

    def text(node):
        return node.text.decode("utf-8") if node else ""

    def field(node, name):
        return node.child_by_field_name(name) if node else None

    def identifiers(node):
        if node is None:
            return []
        return [
            text(n)
            for n in nodes
            if n.type in {"identifier", "shorthand_property_identifier_pattern"}
            and node.start_byte <= n.start_byte
            and n.end_byte <= node.end_byte
        ]

    bindings, writes = Counter(), set()
    for node in nodes:
        if node.type in {
            "variable_declarator",
            "function_declaration",
            "function_expression",
            "class_declaration",
            "class",
            "generator_function_declaration",
        }:
            bindings.update(identifiers(field(node, "name")))
        elif node.type == "formal_parameters":
            for child in node.named_children:
                pattern = (
                    field(child, "pattern")
                    if child.type in {"required_parameter", "optional_parameter"}
                    else child
                )
                bindings.update(identifiers(pattern))
        elif node.type == "arrow_function" and field(node, "parameter"):
            bindings.update(identifiers(field(node, "parameter")))
        elif node.type == "catch_clause":
            bindings.update(identifiers(field(node, "parameter")))
        elif node.type == "import_clause":
            bindings.update(identifiers(node))  # conservative for named aliases
        elif node.type in {
            "assignment_expression",
            "augmented_assignment_expression",
            "update_expression",
        }:
            target = field(node, "left") or field(node, "argument")
            writes.update(identifiers(target))
            if target and target.type in {"member_expression", "subscript_expression"}:
                if "eval" in text(target):
                    writes.add("eval")
        elif node.type == "with_statement":
            return {**empty, "status": "dynamic_scope"}

    factories = set()
    for node in root.named_children:
        if node.type == "import_statement" and text(field(node, "source")) in {
            '"express"',
            "'express'",
        }:
            clauses = [c for c in node.named_children if c.type == "import_clause"]
            if len(clauses) == 1 and len(clauses[0].named_children) == 1:
                binding = clauses[0].named_children[0]
                if (
                    binding.type == "identifier"
                    and bindings[text(binding)] == 1
                    and text(binding) not in writes
                ):
                    factories.add(text(binding))
    apps = set()
    for node in root.named_children:
        if node.type != "lexical_declaration" or not node.text.startswith(b"const "):
            continue
        for declaration in node.named_children:
            name, value = field(declaration, "name"), field(declaration, "value")
            args = field(value, "arguments")
            if (
                name
                and name.type == "identifier"
                and value
                and value.type == "call_expression"
                and text(field(value, "function")) in factories
                and args
                and not args.named_children
                and bindings[text(name)] == 1
                and text(name) not in writes
            ):
                apps.add(text(name))
    sources, sinks = [], []
    for node in nodes:
        if node.type != "call_expression" or any(
            c.type in {"optional_chain", "?."} for c in node.children
        ):
            continue
        func, args = field(node, "function"), field(node, "arguments")
        arguments = args.named_children if args else []
        if (
            func
            and func.type == "identifier"
            and text(func) == "eval"
            and not bindings["eval"]
            and "eval" not in writes
            and len(arguments) == 1
            and arguments[0].type != "spread_element"
            and node.start_point.row == node.end_point.row
        ):
            sinks.append(
                {
                    "line": node.start_point.row + 1,
                    "code": text(node),
                    "argument_code": text(arguments[0]),
                }
            )
        if (
            not func
            or func.type != "member_expression"
            or any(c.type in {"optional_chain", "?."} for c in func.children)
            or text(field(func, "object")) not in apps
            or text(field(func, "property")) not in {"get", "post"}
            or len(arguments) != 2
            or arguments[0].type != "string"
            or arguments[1].type not in {"arrow_function", "function_expression"}
        ):
            continue
        handler = arguments[1]
        params = field(handler, "parameters")
        params = params.named_children if params else []
        if len(params) != 2:
            continue
        parameter = params[0]
        if parameter.type == "required_parameter":
            parameter = field(parameter, "pattern")
        if not parameter or parameter.type != "identifier":
            continue
        receiver = text(parameter)
        if bindings[receiver] != 1 or receiver in writes:
            continue
        body = field(handler, "body")
        for access in nodes:
            if (
                not body
                or access.type != "member_expression"
                or access.start_point.row != access.end_point.row
                or not body.start_byte <= access.start_byte < access.end_byte <= body.end_byte
            ):
                continue
            inner = field(access, "object")
            if (
                inner
                and inner.type == "member_expression"
                and text(field(inner, "object")) == receiver
                and text(field(inner, "property")) in {"query", "body", "params"}
                and field(access, "property").type == "property_identifier"
                and not any(
                    c.type in {"optional_chain", "?."} for c in access.children + inner.children
                )
            ):
                sources.append({"line": access.start_point.row + 1, "code": text(access)})
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
