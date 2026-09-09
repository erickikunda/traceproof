"""Bounded subprocess parser. Never imports or executes repository code."""

import ast
import json
import resource
import sys

MAX_BYTES = 1024 * 1024
MAX_NODES = 50_000


def parse(source: bytes) -> dict:
    if len(source) > MAX_BYTES:
        return {"status": "size_limit", "symbols": [], "calls": []}
    try:
        tree = ast.parse(source)
        if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
            return {"status": "node_limit", "symbols": [], "calls": []}
        symbols, calls = [], []

        def visit(node, scope):
            if isinstance(node, ast.Call):
                # Names/attributes are syntax only: Python permits rebinding and dispatch.
                parts, target = [], node.func
                while isinstance(target, ast.Attribute):
                    parts.append(target.attr)
                    target = target.value
                if isinstance(target, ast.Name):
                    parts.append(target.id)
                else:
                    parts.append("<dynamic>")
                calls.append(
                    {
                        "caller": scope,
                        "line": node.lineno,
                        "column": node.col_offset,
                        "end_line": node.end_lineno,
                        "expression": ".".join(reversed(parts)),
                        "resolution": "unresolved",
                    }
                )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{scope}.{node.name}" if scope != "<module>" else node.name
                symbols.append(
                    {
                        "name": name,
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                        "async": isinstance(node, ast.AsyncFunctionDef),
                    }
                )
                # Decorators, defaults, bases and annotations execute in the outer scope.
                for field, value in ast.iter_fields(node):
                    values = value if isinstance(value, list) else [value]
                    for child in values:
                        if isinstance(child, ast.AST):
                            visit(child, name if field == "body" else scope)
                return
            if isinstance(node, ast.Lambda):
                visit(node.args, scope)
                visit(node.body, f"{scope}.<lambda@{node.lineno}:{node.col_offset}>")
                return
            for child in ast.iter_child_nodes(node):
                visit(child, scope)

        visit(tree, "<module>")
        return {"status": "parsed", "symbols": symbols, "calls": calls}
    except (SyntaxError, ValueError, UnicodeError):
        return {"status": "parse_error", "symbols": [], "calls": []}
    except (RecursionError, MemoryError):
        return {"status": "resource_limit", "symbols": [], "calls": []}


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    # macOS does not reliably support RLIMIT_AS. Production also needs pod limits.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    print(json.dumps(parse(sys.stdin.buffer.read(MAX_BYTES + 1))))
