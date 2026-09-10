"""Bounded C# syntax anchors for advisory review; no symbol binding proof."""

import json
import resource
import sys

import tree_sitter_c_sharp
from tree_sitter import Language, Parser

MAX_BYTES = 16 * 1024
MAX_NODES = 50_000


def classic_source(parameter, imports):
    """Recognize only direct public HttpGet actions; still no framework binding proof."""
    method = parameter.parent.parent if parameter.parent else None
    owner = method.parent.parent if method and method.parent else None
    if (
        not method
        or method.type != "method_declaration"
        or not owner
        or owner.type != "class_declaration"
    ):
        return False
    modifiers = {n.text.decode() for n in method.children if n.type == "modifier"}
    if "public" not in modifiers or modifiers & {"static", "abstract", "override"}:
        return False
    owner_modifiers = {n.text.decode() for n in owner.children if n.type == "modifier"}
    if "public" not in owner_modifiers or owner_modifiers & {"abstract", "static"}:
        return False
    if any(n.type == "type_parameter_list" for target in (owner, method) for n in target.children):
        return False
    kind = parameter.child_by_field_name("type")
    if kind is None or kind.text != b"string":
        return False
    bases = [n for n in owner.named_children if n.type == "base_list"]
    if len(bases) != 1 or len(bases[0].named_children) != 1:
        return False
    base = bases[0].named_children[0].text.decode()
    namespaces = ("System.Web.Mvc", "System.Web.Http")
    for namespace, controller in zip(namespaces, ("Controller", "ApiController"), strict=True):
        if base not in {controller, namespace + "." + controller}:
            continue
        if base == controller and f"using {namespace};" not in imports:
            continue
        if any(
            f"using {other};" in imports
            for other in (*namespaces, "Microsoft.AspNetCore.Mvc")
            if other != namespace
        ):
            return False

        def attributes(target):
            return [
                a.child_by_field_name("name").text.decode()
                for group in target.named_children
                if group.type == "attribute_list"
                for a in group.named_children
                if a.type == "attribute"
            ]

        def qualified(name, short, namespace=namespace):
            return name in {namespace + "." + short, namespace + "." + short + "Attribute"} or (
                name in {short, short + "Attribute"} and f"using {namespace};" in imports
            )

        attrs = attributes(method)
        if not any(qualified(n, "HttpGet") for n in attrs) or any(
            not any(qualified(n, allowed) for allowed in ("HttpGet", "Route")) for n in attrs
        ):
            return False
        params = attributes(parameter)
        return (
            not params
            if namespace == "System.Web.Mvc"
            else (len(params) == 1 and qualified(params[0], "FromUri"))
        )
    return False


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
            if name and name.text.decode() in {
                "FromQuery",
                "FromQueryAttribute",
                "FromUri",
                "FromUriAttribute",
                "Controller",
                "ApiController",
                "HttpGet",
                "HttpGetAttribute",
                "Route",
                "RouteAttribute",
            }:
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
        if node.type == "parameter" and classic_source(node, imports):
            sources.append(location)
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
