"""Go package and symbol evidence from first-party source; absence never establishes safety."""

import re
from collections import Counter, defaultdict

from traceproof.dependency_usage import GO_SUFFIXES, first_party, read_source

IMPORT_LINE = re.compile(r'^\s*(?:(\.|_|[A-Za-z_][A-Za-z0-9_]*)\s+)?"([^"\n]{1,512})"')
MAJOR_SUFFIX = re.compile(r"^v\d+$")
GOPKG_SUFFIX = re.compile(r"\.v\d+$")
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

MAX_SOURCE_FILES = 20_000
MAX_REQUIREMENTS = 2_000
MAX_RECORDED_SYMBOLS = 20


def default_identifier(path):
    """Derive the identifier an unaliased import binds; this follows convention, not declaration."""
    parts = [part for part in path.split("/") if part]
    if not parts:
        return None
    last = parts[-1]
    if MAJOR_SUFFIX.match(last) and len(parts) > 1:
        last = parts[-2]
    last = GOPKG_SUFFIX.sub("", last)
    return last if IDENTIFIER.match(last) else None


def import_bindings(text):
    """Map the identifier each import binds to its path; dot imports bind nothing nameable."""
    bindings, dotted, block = {}, 0, False
    for line in text.splitlines():
        body = line.partition("//")[0].strip()
        if block:
            if body.startswith(")"):
                block = False
                continue
        elif body.startswith("import ("):
            block = True
            continue
        elif body.startswith("import "):
            body = body[len("import ") :].strip()
        else:
            continue
        match = IMPORT_LINE.match(body)
        if match is None:
            continue
        alias, path = match.group(1), match.group(2)
        if alias == ".":
            # A dot import puts symbols in scope unqualified; no reference is nameable.
            dotted += 1
            bindings.setdefault(None, set()).add(path)
            continue
        identifier = None if alias == "_" else (alias or default_identifier(path))
        bindings.setdefault(identifier, set()).add(path)
    return bindings, dotted


def requirements_of(matches):
    wanted = defaultdict(set)
    constrained = 0
    for match in matches:
        for entry in match.get("affected_imports") or ():
            if len(wanted) >= MAX_REQUIREMENTS:
                break
            wanted[entry["path"]].update(entry["symbols"])
            constrained += bool(entry["platform_constrained"])
    return wanted, constrained


def referenced_symbols(text, identifier, symbols):
    """A method symbol is searched by its receiver type; a call site is not resolved here."""
    found = set()
    for symbol in symbols:
        root = symbol.split(".")[0]
        if not IDENTIFIER.match(root):
            continue
        if re.search(rf"\b{re.escape(identifier)}\.{re.escape(root)}\b", text):
            found.add(symbol)
    return found


def scan(manifest, tree, wanted):
    imported, referenced, skipped, scanned = set(), defaultdict(set), Counter(), 0
    dotted = 0
    selected = [
        record
        for record in sorted(manifest.files, key=lambda item: item.path)
        if record.path.endswith(GO_SUFFIXES) and first_party(record.path)
    ]
    for record in selected[:MAX_SOURCE_FILES]:
        text, reason = read_source(tree, record)
        if reason is not None:
            skipped[f"go:{reason}"] += 1
            continue
        scanned += 1
        bindings, file_dotted = import_bindings(text)
        dotted += file_dotted
        for identifier, paths in bindings.items():
            imported |= paths
            if identifier is None:
                continue
            for path in paths & set(wanted):
                referenced[path] |= referenced_symbols(text, identifier, wanted[path])
    return {
        "imported": imported,
        "referenced": referenced,
        "files_scanned": scanned,
        "files_skipped": dict(sorted(skipped.items())),
        "dot_imports": dotted,
    }


def classify(match, evidence):
    """Name what was seen; a vulnerable package left unimported is not a safety conclusion."""
    if not evidence["files_scanned"]:
        return "not_evaluated", []
    entries = match.get("affected_imports") or []
    if not entries:
        return "no_symbol_data", []
    paths = [entry["path"] for entry in entries]
    found = sorted({s for path in paths for s in evidence["referenced"].get(path, ())})
    if found:
        return "symbol_referenced", found[:MAX_RECORDED_SYMBOLS]
    if any(path in evidence["imported"] for path in paths):
        return "package_imported", []
    return "package_not_imported", []


def evaluate_symbols(manifest, tree, matches):
    """Attach Go package/symbol evidence; this resolves no call graph and proves no execution."""
    go_matches = [match for match in matches if match.get("ecosystem") == "go"]
    wanted, constrained = requirements_of(go_matches)
    evidence = scan(manifest, tree, wanted) if go_matches else None
    states, results = Counter(), {}
    for match in go_matches:
        state, symbols = (
            classify(match, evidence) if evidence is not None else ("not_evaluated", [])
        )
        states[state] += 1
        results[f"{match['osv_id']}|{match['component_ref']}"] = {
            "state": state,
            "symbols_referenced": symbols,
        }
    return {
        "symbol_evidence": results,
        "coverage": {
            "analysis": "package and symbol references; not reachability",
            "detection_method": "lexical qualified-reference scan",
            "go_matches_considered": len(go_matches),
            "advisories_with_symbol_data": sum(
                1 for match in go_matches if match.get("affected_imports")
            ),
            "platform_constrained_entries": constrained,
            "symbol_states": dict(sorted(states.items())),
            "source_files_scanned": evidence["files_scanned"] if evidence else 0,
            "source_files_skipped": evidence["files_skipped"] if evidence else {},
            "dot_imports_unresolvable": evidence["dot_imports"] if evidence else 0,
            "call_graph_resolved": False,
            "third_party_source_available": False,
            "platform_filtering": "none",
        },
    }
