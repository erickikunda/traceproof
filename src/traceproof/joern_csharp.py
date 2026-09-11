"""Opt-in repaired C# tooling and conservative source mapping; discovery only."""

import hashlib
import json
import os
from pathlib import Path

from traceproof.csharp_locations import validate_locations
from traceproof.domain import TraceProofError

PATCHED_SHA256 = "81bd230f4a7b6cfd12da1ce4135251003cb7563ad72b82c18aeef643603c05a0"


def repaired_frontend(store, home, repair):
    try:
        repair = repair.resolve(strict=True)
        forbidden = [store.root / "artifacts", store.root / "scans"]
        if any(repair.is_relative_to(p.resolve()) for p in forbidden):
            raise ValueError()
        receipt_bytes = (repair / "build-receipt.json").read_bytes()
        if len(receipt_bytes) > 1024 * 1024:
            raise ValueError()
        receipt = json.loads(receipt_bytes)
        if receipt["manifest"]["patched_source_sha256"] != PATCHED_SHA256:
            raise ValueError()
        if hashlib.sha256((repair / "AstCreator.scala").read_bytes()).hexdigest() != PATCHED_SHA256:
            raise ValueError()
        classes = repair / "classes"
        recorded = receipt["class_sha256"]
        actual = {str(p.relative_to(classes)) for p in classes.rglob("*") if p.is_file()}
        if not actual or actual != set(recorded):
            raise ValueError()
        for relative, digest in recorded.items():
            path = (classes / relative).resolve(strict=True)
            path.relative_to(classes)
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError()
        jars = []
        for filename, digest in receipt["jar_sha256"].items():
            path = Path(filename).resolve(strict=True)
            path.relative_to(home)
            if path.suffix != ".jar" or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError()
            jars.append(str(path))
        if not jars:
            raise ValueError()
        classpath = os.pathsep.join([str(classes), *jars])
        return ["java", "-Xmx2g", "-cp", classpath, "io.joern.csharpsrc2cpg.Main"], {
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "patched_source_sha256": PATCHED_SHA256,
            "publisher_authenticated": False,
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise TraceProofError("Invalid or modified operator C# repair build") from None


def map_output(doc, source, selected, *, require_query_source=False):
    records = {r.path: r for r in selected}
    mapped, audit = [], []
    if len(doc["paths"]) > 10_000:
        raise TraceProofError("Too many C# paths")
    for flow in doc["paths"]:
        if not isinstance(flow, list) or not 1 <= len(flow) <= 256:
            raise TraceProofError("Invalid C# flow size")
        results, nodes = [], []
        for node in flow:
            try:
                path = Path(node["file"])
                if path.is_absolute():
                    path = path.relative_to(source)
                relative = path.as_posix()
                if ".." in path.parts or relative not in records:
                    raise ValueError()
                result = validate_locations(
                    (source / path).read_bytes(),
                    records[relative].sha256,
                    [node],
                    framework_facts=True,
                )
            except (ValueError, TypeError, KeyError):
                raise TraceProofError("Invalid C# source reference") from None
            results.append(result)
            if result["status"] == "parsed" and result["nodes"][0]["status"] == "validated_span":
                span = result["nodes"][0]["span"]
                nodes.append({**node, "file": relative, "line": span["line"]})
        source_verified = bool(
            results
            and results[0].get("nodes")
            and any(
                fact.get("category") == "sources"
                for fact in results[0]["nodes"][0].get("framework_facts", [])
            )
        )
        valid = len(nodes) == len(flow) and (not require_query_source or source_verified)
        audit.append(
            {"published": valid, "query_source_verified": source_verified, "nodes": results}
        )
        if valid:
            mapped.append(nodes)
    return json.dumps({**doc, "paths": mapped, "flow_count": len(mapped)}).encode(), {
        "validated_paths": len(mapped),
        "unsupported_paths": len(doc["paths"]) - len(mapped),
        "qualification": "syntax_spans_only",
        "paths": audit,
    }
