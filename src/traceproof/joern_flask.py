"""Bounded syntax endpoint selection; never imports repository code."""

import ast
import json
import os
import resource
import subprocess
import sys
from pathlib import Path

RULE = "traceproof/joern-python-flask-system-v1"
PROFILE = "python-flask-system-v1"


def endpoints(source, include_code=False):
    if len(source) > 1024 * 1024:
        return {"status": "size_limit", "sources": [], "sinks": []}
    try:
        tree = ast.parse(source)
        nodes = list(ast.walk(tree))
        if len(nodes) > 50000:
            raise ValueError()
    except (SyntaxError, ValueError, RecursionError):
        return {"status": "unsupported_syntax", "sources": [], "sinks": []}
    bindings = {}
    imports = {}
    for node in nodes:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imports[name] = imports.get(name, 0) + 1
                if (
                    node in tree.body
                    and isinstance(node, ast.ImportFrom)
                    and node.module == "flask"
                    and not node.level
                    and alias.name == "request"
                ):
                    bindings[name] = "request"
                if node in tree.body and isinstance(node, ast.Import) and alias.name == "os":
                    bindings[name] = "os"
                if alias.name == "*":
                    return {"status": "wildcard_import", "sources": [], "sinks": []}
    for name in list(bindings):
        if imports[name] != 1:
            del bindings[name]
            continue
        for node in nodes:
            target = node
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
                while isinstance(target, ast.Attribute):
                    target = target.value
            if (
                (
                    isinstance(target, ast.Name)
                    and target.id == name
                    and (isinstance(target.ctx, (ast.Store, ast.Del)) or target is not node)
                )
                or (isinstance(node, ast.arg) and node.arg == name)
                or (
                    isinstance(
                        node,
                        (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.ExceptHandler),
                    )
                    and node.name == name
                )
                or (isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == name)
                or (isinstance(node, ast.MatchMapping) and node.rest == name)
            ):
                del bindings[name]
                break
    result = {"status": "parsed", "sources": [], "sinks": []}
    for node in nodes:
        if not isinstance(node, ast.Call) or node.lineno != node.end_lineno:
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        value = func.value
        if (
            func.attr == "get"
            and isinstance(value, ast.Attribute)
            and value.attr in {"args", "form"}
            and isinstance(value.value, ast.Name)
            and bindings.get(value.value.id) == "request"
            and len(node.args) == 1
            and not node.keywords
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            result["sources"].append(
                {
                    "line": node.lineno,
                    "name": "get",
                    **(
                        {
                            "code": ast.get_source_segment(
                                source.decode("utf-8") if isinstance(source, bytes) else source,
                                node,
                            )
                        }
                        if include_code
                        else {}
                    ),
                }
            )
        if (
            func.attr == "system"
            and isinstance(value, ast.Name)
            and bindings.get(value.id) == "os"
            and len(node.args) == 1
            and not node.keywords
        ):
            result["sinks"].append(
                {
                    "line": node.lineno,
                    "name": "system",
                    **(
                        {
                            "argument_code": ast.get_source_segment(
                                source.decode("utf-8") if isinstance(source, bytes) else source,
                                node.args[0],
                            ),
                            "code": ast.get_source_segment(
                                source.decode("utf-8") if isinstance(source, bytes) else source,
                                node,
                            ),
                        }
                        if include_code
                        else {}
                    ),
                }
            )
    return result


def parse_isolated(source, include_code=False):
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-I",
                str(Path(__file__).resolve()),
                *(["--include-code"] if include_code else []),
            ],
            input=source,
            capture_output=True,
            timeout=10,
            env={"PATH": os.defpath},
        )
        if proc.returncode:
            raise ValueError()
        return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return {"status": "parser_failed", "sources": [], "sinks": []}


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    print(
        json.dumps(endpoints(sys.stdin.buffer.read(1024 * 1024 + 1), "--include-code" in sys.argv))
    )
