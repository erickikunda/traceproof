"""Bounded subprocess parser. Never imports or executes repository code."""

import ast
import json
import resource
import sys
from collections import Counter

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
        bindings = Counter()
        unsafe = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bindings[node.name] += 1
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                bindings[node.id] += 1
            elif isinstance(node, ast.arg):
                bindings[node.arg] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    bindings[alias.asname or alias.name.split(".")[0]] += 1
                    unsafe |= alias.name == "*"
            elif isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)) and node.name:
                bindings[node.name] += 1
            elif isinstance(node, ast.MatchMapping) and node.rest:
                bindings[node.rest] += 1
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                unsafe = True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                unsafe |= node.func.id in {"exec", "eval", "globals", "locals", "setattr"}
        exports, imports = {}, {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.decorator_list and bindings[node.name] == 1:
                    exports[node.name] = {"line": node.lineno, "end_line": node.end_lineno}
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                for alias in node.names:
                    name = alias.asname or alias.name
                    if bindings[name] == 1:
                        imports[name] = {"module": node.module, "symbol": alias.name}
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if bindings[name] == 1:
                        imports[alias.asname or alias.name] = {"module": alias.name, "symbol": None}
        return {
            "status": "parsed",
            "symbols": symbols,
            "calls": calls,
            "bindings": {"exports": exports, "imports": imports, "unsafe": unsafe},
        }
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
