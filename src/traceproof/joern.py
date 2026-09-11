"""Experimental durable discovery with explicit, bounded Joern profiles."""

import hashlib
import json
import os
import signal
import subprocess
from collections import Counter
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.intake import now
from traceproof.joern_diagnostics import observe_logs
from traceproof.persistence import Candidate, ScanAttempt, exclusive_worker
from traceproof.sarif import MAX_SARIF_BYTES, normalize

VERSION = "4.0.625"
RULE = "traceproof/joern-spring-get-jdbc-sql-v1"
SUFFIXES = {
    "java": ".java",
    "csharp": ".cs",
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "go": ".go",
    "rust": ".rs",
    "c": (".c", ".h"),
    "cpp": (".cpp", ".h", ".hpp"),
}
PYTHON_RULE = "traceproof/joern-python-lookup-system-v1"


def stage(command, root, name, timeout, *, rust_home=None):
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(root),
        "TMPDIR": str(root),
        "LANG": "en_US.UTF-8",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "GOTOOLCHAIN": "local",
    }
    if rust_home is not None:
        env.update(
            PATH=str(rust_home / "bin") + os.pathsep + env["PATH"],
            CARGO_HOME=str(root / "cargo-home"),
            CARGO_NET_OFFLINE="true",
        )
    if os.environ.get("JAVA_HOME"):
        env["JAVA_HOME"] = os.environ["JAVA_HOME"]
    with (root / f"{name}.log").open("wb") as log:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TraceProofError(f"Joern {name} timed out") from None
    if code:
        raise TraceProofError(f"Joern {name} failed; inspect stage log")


def decode_output(raw, language="java", rule=RULE):
    if len(raw) > MAX_SARIF_BYTES:
        raise TraceProofError("Joern output exceeds 16 MiB")
    try:
        doc = json.loads(raw)
        if doc["schema_version"] != "2" or doc["engine_id"] != "joern" or doc["rule_id"] != rule:
            raise ValueError()
        for key in ("source_count", "sink_count", "flow_count"):
            if type(doc[key]) is not int or not 0 <= doc[key] <= 1_000_000:
                raise ValueError()
        if not isinstance(doc["paths"], list) or doc["flow_count"] != len(doc["paths"]):
            raise ValueError()
        if doc["flow_count"] and (not doc["source_count"] or not doc["sink_count"]):
            raise ValueError()
        represented = doc[f"represented_{language}_files"]
        if not isinstance(represented, list) or len(represented) > 100_000:
            raise ValueError()
        if any(not isinstance(path, str) or not path for path in represented):
            raise ValueError()
        return doc
    except (ValueError, KeyError, TypeError, RecursionError):
        raise TraceProofError("Malformed Joern coverage/output contract") from None


def discovery_coverage(doc, source, selected, language="java"):
    expected = {record.path for record in selected}
    represented = set()
    try:
        for value in doc[f"represented_{language}_files"]:
            path = Path(value)
            if path.is_absolute():
                path = path.relative_to(source)
            if ".." in path.parts or path.as_posix() not in expected:
                raise ValueError()
            represented.add(path.as_posix())
    except ValueError:
        raise TraceProofError("Graph inventory references unexpected source") from None
    if doc["flow_count"]:
        observation = "modeled_flows_found"
    elif not doc["source_count"] and not doc["sink_count"]:
        observation = "no_modeled_sources_or_sinks"
    elif not doc["source_count"]:
        observation = "no_modeled_sources"
    elif not doc["sink_count"]:
        observation = "no_modeled_sinks"
    else:
        observation = "no_recorded_flow_between_modeled_endpoints"
    return {
        "schema_version": "1",
        "observation": observation,
        f"selected_{language}_files": len(expected),
        f"represented_{language}_files": len(represented),
        "missing_graph_files": sorted(expected - represented),
        "modeled_source_count": doc["source_count"],
        "modeled_sink_count": doc["sink_count"],
        "recorded_flow_count": doc["flow_count"],
        "parser_diagnostics": "not_qualified",
        "parse_completeness_verified": False,
        "reachability_verified": False,
        "interpretation": "Graph representation and modeled endpoints are not complete coverage",
    }


def to_sarif(raw, source, manifest, language="java", rule=RULE):
    """Preserve recorded flow order; reject invalid references instead of inventing nodes."""
    if len(raw) > MAX_SARIF_BYTES:
        raise TraceProofError("Joern output exceeds 16 MiB")
    try:
        doc = decode_output(raw, language, rule)
        paths = doc["paths"]
        if not isinstance(paths, list) or len(paths) > 10000 or doc["flow_count"] != len(paths):
            raise ValueError()
        records = {f.path: f for f in manifest.files if f.path.endswith(SUFFIXES[language])}
        results = []
        for flow in paths:
            if not isinstance(flow, list) or not 1 <= len(flow) <= 1000:
                raise ValueError()
            locations = []
            for node in flow:
                path = Path(node["file"])
                if path.is_absolute():
                    path = path.relative_to(source)
                if ".." in path.parts or path.as_posix() not in records:
                    raise ValueError()
                line = node["line"]
                text = (source / path).read_text()
                if type(line) is not int or not 1 <= line <= len(text.splitlines()):
                    raise ValueError()
                locations.append(
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": path.as_posix()},
                            "region": {"startLine": line},
                        }
                    }
                )
            results.append(
                {
                    "ruleId": rule,
                    "message": {
                        "text": (
                            "CWE-22: Spring input to Files.readAllBytes path; escape unverified."
                            if rule == "traceproof/joern-spring-get-file-path-v1"
                            else "CWE-22: Flask input to file path; directory escape unverified."
                            if rule == "traceproof/joern-python-flask-path-v1"
                            else "Environment value to shell command text; discovery only."
                            if rule == "traceproof/joern-rust-env-shell-v1"
                            else "Command-line argument to system command text; discovery only."
                            if rule.endswith("-argv-system-v1")
                            else "Go HTTP form input to shell command text; discovery only."
                            if rule == "traceproof/joern-go-http-shell-v1"
                            else "Express request property to builtin eval; discovery only."
                            if rule.endswith("-express-eval-v1")
                            else "Flask request input to os.system; discovery only."
                            if rule == "traceproof/joern-python-flask-system-v1"
                            else "Spring GET parameter to JDBC SQL argument flow; discovery only."
                            if language == "java"
                            else "Experimental lookup(input)/system flow; discovery only."
                            if language in {"python", "c", "cpp"}
                            else "Experimental lookup(input)/eval flow; discovery only."
                            if language in {"javascript", "typescript"}
                            else "Experimental lookup(input)/Command flow; discovery only."
                            if language == "go"
                            else "Experimental lookup(input)/arg flow; discovery only."
                            if language == "rust"
                            else "Experimental Lookup(name) to CommandText flow; discovery only."
                        )
                    },
                    "locations": [locations[-1]],
                    "codeFlows": [
                        {"threadFlows": [{"locations": [{"location": loc} for loc in locations]}]}
                    ],
                }
            )
        return json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "Joern", "version": VERSION}},
                        "invocations": [{"executionSuccessful": False}],
                        "results": results,
                    }
                ],
            }
        ).encode()
    except (ValueError, KeyError, TypeError, OSError, AttributeError, RecursionError):
        raise TraceProofError("Invalid Joern output or source reference") from None


def discover(
    store,
    run_id,
    joern_home,
    timeout=180,
    *,
    repair_dir=None,
    language=None,
    rust_home=None,
    extraction_timeout=None,
    discovery_profile=None,
):
    """Explicit local opt-in; caller supplies trusted tools, never repository scripts."""
    language = language or ("csharp" if repair_dir is not None else "java")
    if language not in SUFFIXES or (language == "csharp") != (repair_dir is not None):
        raise TraceProofError("Unsupported Joern language/repair combination")
    supported_profiles = {
        "python-flask-system-v1": {"python"},
        "python-flask-path-v1": {"python"},
        "java-spring-file-path-v1": {"java"},
        "express-request-eval-v1": {"javascript", "typescript"},
        "go-http-shell-v1": {"go"},
        "rust-env-shell-v1": {"rust"},
        "c-family-argv-system-v1": {"c", "cpp"},
    }
    if discovery_profile is not None and language not in supported_profiles.get(
        discovery_profile, set()
    ):
        raise TraceProofError("Unsupported Joern discovery profile/language")
    rust_toolchain = None
    if language == "rust":
        from traceproof.joern_rust import trusted_toolchain

        rust_toolchain = trusted_toolchain(store, rust_home)
    elif rust_home is not None:
        raise TraceProofError("Rust toolchain only applies to Rust scans")
    stage_options = {"rust_home": rust_toolchain} if rust_toolchain else {}
    rule = {
        "java": RULE,
        "csharp": "traceproof/joern-csharp-lookup-commandtext-v1",
        "python": PYTHON_RULE,
        "javascript": "traceproof/joern-javascript-lookup-eval-v1",
        "typescript": "traceproof/joern-typescript-lookup-eval-v1",
        "go": "traceproof/joern-go-lookup-command-v1",
        "rust": "traceproof/joern-rust-lookup-arg-v1",
        "c": "traceproof/joern-c-lookup-system-v1",
        "cpp": "traceproof/joern-cpp-lookup-system-v1",
    }[language]
    if discovery_profile == "python-flask-system-v1":
        from traceproof.joern_flask import RULE as flask_rule

        rule = flask_rule
    elif discovery_profile == "java-spring-file-path-v1":
        rule = "traceproof/joern-spring-get-file-path-v1"
    elif discovery_profile == "python-flask-path-v1":
        rule = "traceproof/joern-python-flask-path-v1"
    elif discovery_profile == "express-request-eval-v1":
        rule = f"traceproof/joern-{language}-express-eval-v1"
    if discovery_profile == "go-http-shell-v1":
        rule = "traceproof/joern-go-http-shell-v1"
    if discovery_profile == "c-family-argv-system-v1":
        rule = f"traceproof/joern-{language}-argv-system-v1"
    if discovery_profile == "rust-env-shell-v1":
        rule = "traceproof/joern-rust-env-shell-v1"
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise TraceProofError("Timeout must be between 1 and 3600 seconds")
    extraction_timeout = timeout if extraction_timeout is None else extraction_timeout
    if type(extraction_timeout) is not int or not 1 <= extraction_timeout <= 3600:
        raise TraceProofError("Extraction timeout must be between 1 and 3600 seconds")
    home = Path(joern_home).resolve(strict=True)
    if not (home / "lib" / f"io.joern.joern-cli-{VERSION}.jar").is_file():
        raise TraceProofError("Expected pinned Joern version layout not found")
    if home.is_relative_to(store.root / "artifacts") or home.is_relative_to(store.root / "scans"):
        raise TraceProofError("Joern must come from operator tooling, not scan artifacts")
    frontend_name = {
        "java": "javasrc2cpg",
        "csharp": "javasrc2cpg",
        "python": "pysrc2cpg",
        "javascript": "jssrc2cpg.sh",
        "typescript": "jssrc2cpg.sh",
        "go": "gosrc2cpg",
        "rust": "rust2cpg",
        "c": "c2cpg.sh",
        "cpp": "c2cpg.sh",
    }[language]
    frontend = [str(home / frontend_name), "-J-Xmx2g"]
    repair_identity = None
    if repair_dir is not None:
        from traceproof.joern_csharp import repaired_frontend

        frontend, repair_identity = repaired_frontend(store, home, Path(repair_dir))
    store.require_initialized()
    with exclusive_worker(store.root):
        run, manifest, tree = verified_source(store, run_id)
        selected = [f for f in manifest.files if f.path.endswith(SUFFIXES[language])]
        if not selected:
            raise TraceProofError(f"Snapshot contains no {language} source")
        cargo = None
        if language == "rust":
            from traceproof.joern_rust import cargo_manifest

            cargo = cargo_manifest(tree, manifest)
        prepared = selected + (
            [f for f in manifest.files if Path(f.path).name == "go.mod"] if language == "go" else []
        )
        attempt_id = str(uuid4())
        root = store.root / "scans" / attempt_id
        root.mkdir(parents=True, mode=0o700)
        source = root / "source"
        report = {
            "schema_version": "1",
            "report_kind": "static_candidates",
            "attempt_id": attempt_id,
            "run_id": run_id,
            "repo_id": run.repo_id,
            "snapshot_id": manifest.snapshot_id,
            "classification": manifest.classification,
            "language": language,
            "discovery_profile": discovery_profile or "default",
            "status": "running",
            "scanner": {
                "engine_id": "joern",
                "version": VERSION,
                "adapter_version": "experimental-csharp-1"
                if repair_dir
                else "experimental-python-1"
                if language == "python"
                else f"experimental-{language}-1"
                if language in {"javascript", "typescript", "go", "rust", "c", "cpp"}
                else "experimental-4",
            },
            "prepared_input": {"kind": "joern_cpg", "path": str(root / "cpg.bin")},
            "candidate_count": None,
            "verified_finding_count": None,
            "coverage_verified": False,
            "security_verdict": "not_adjudicated",
            "network_isolated": False,
            "automatic_reuse_eligible": False,
            "timeout_seconds_per_stage": timeout,
            "extraction_timeout_seconds": extraction_timeout,
            "query_timeout_seconds": timeout,
            "requested_heap_mb_per_jvm": 2048,
            "raw_sarif_path": str(root / "results.sarif"),
            "log_path": str(root / "analyze.log"),
            "limitations": [
                "Public Spring GetMapping String RequestParam only; other sources omitted.",
                "Exact JDBC Statement.executeQuery(String) graph signature only.",
                "Java source only; dependencies, builds and other languages omitted.",
                "Discovery only; no qualified triage or clean security verdict.",
                "Version layout checked; installed tool contents not cryptographically verified.",
                "Network not isolated; automatic result reuse disabled.",
            ],
            "omitted_file_count": len(manifest.files) - len(prepared),
        }
        if discovery_profile == "java-spring-file-path-v1":
            report["cwe_scope"] = ["CWE-22"]
            report["limitations"] = [
                "Spring GET String RequestParam to Files.readAllBytes(Path) only.",
                "Modeled Path propagation is not proof of directory escape or runtime identity.",
                "Confinement, guards and deployment access unverified; advisory unsupported.",
                "Discovery only; incomplete coverage and no clean verdict.",
            ]
        if language == "python":
            report["limitations"] = [
                "Experimental lookup(input) parameter to call named system argument profile only.",
                "Python source only; frameworks, dependencies and other languages omitted.",
                "Call names do not authenticate os.system or prove runtime reachability.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Version layout checked; trusted operator tooling required.",
                "Network not isolated by this command; automatic result reuse disabled.",
            ]
        if discovery_profile == "python-flask-system-v1":
            report["limitations"] = [
                "Single-line Flask request.args/form.get(string) to os.system argument only.",
                "Top-level imports and no obvious rebinding required; aliases supported.",
                "Dynamic monkeypatching, module resolution and HTTP reachability unqualified.",
                "Ambiguous graph endpoints withheld; synthetic intermediate nodes retained.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Trusted tools required; command does not enforce OS network isolation.",
            ]
        if discovery_profile == "python-flask-path-v1":
            report["limitations"] = [
                "CWE-22 candidate: Flask args/form.get to unshadowed open read-path argument.",
                "Single-line calls, positional paths, optional constant read mode only.",
                "Directory confinement, guards and runtime builtin identity unverified.",
                "Discovery only; advisory unsupported; no clean verdict or complete coverage.",
            ]
            report["cwe_scope"] = ["CWE-22"]
        if language in {"javascript", "typescript"}:
            report["limitations"] = [
                "Experimental lookup(input) parameter to call named eval argument profile only.",
                f"Only {SUFFIXES[language]} copied; mixed-language flows and JSX/TSX omitted.",
                "Frameworks, project configuration, dependencies and builds omitted.",
                "Call names do not authenticate builtin eval or prove runtime reachability.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Version layout checked; trusted operator tooling required.",
                "Network not isolated by this command; automatic result reuse disabled.",
            ]
        if language == "go":
            report["limitations"] = [
                "Experimental lookup(input) to call named Command argument 3 profile only.",
                "Only .go files and go.mod metadata copied; dependencies/builds omitted.",
                "Call names do not authenticate os/exec.Command or prove shell execution.",
                "Frameworks, cgo, build tags and advanced language semantics unqualified.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Version layout checked; trusted operator tooling required.",
                "Go proxy/checksum downloads disabled; OS network isolation still required.",
            ]
        if discovery_profile == "go-http-shell-v1":
            report["limitations"] = [
                "net/http Request FormValue/PostFormValue graph signatures only.",
                "os/exec.Command with literal sh/bash or /bin/sh /bin/bash, then -c only.",
                "Command construction does not prove execution or HTTP route reachability.",
                "Graph identities, dynamic mutation and sanitization are not qualified.",
                "CommandContext, other shells, flags and HTTP sources omitted.",
                "Only .go and go.mod copied; dependencies/builds and mixed languages omitted.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Go downloads disabled; command does not enforce OS network isolation.",
            ]
        if discovery_profile == "express-request-eval-v1":
            report["limitations"] = [
                "Express graph signatures for get/post and inline callback argument 2 only.",
                "Factory import aliases are not qualified; dependencies/builds are omitted.",
                "First callback parameter query/body/params field reads; builtin eval signature.",
                "Graph resolution is not proof of package identity or HTTP/runtime reachability.",
                "Routers, middleware, named callbacks, computed properties and JSX/TSX omitted.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Trusted tools required; command does not enforce OS network isolation.",
            ]
        if language in {"c", "cpp"}:
            report["limitations"] = [
                "Experimental lookup(input) to call named system argument 1 profile only.",
                "Only .c/.h or .cpp/.h/.hpp files selected; other extensions omitted.",
                "Source-only parsing; build settings and compilation databases omitted.",
                "Call names do not authenticate system identity or prove runtime reachability.",
                "C++ classes, templates, virtual dispatch and memory-safety rules unqualified.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Trusted tools required; command does not enforce OS network isolation.",
            ]
        if discovery_profile == "c-family-argv-system-v1":
            report["limitations"] = [
                "Global main second char**/char*[] parameter, positive decimal index reads only.",
                "C++ system namespace/signature is unresolved; libc identity is unqualified.",
                "Any local system definition withholds all sinks conservatively.",
                "Graph signatures do not authenticate libc or prove runtime reachability.",
                "Aliases, variable indices, macros and build configurations are unqualified.",
                "C-style C++ only; classes, templates and memory-safety coverage unqualified.",
                "Only selected source/header suffixes copied; dependencies/builds omitted.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Trusted tools required; command does not enforce OS network isolation.",
            ]
        if language == "rust":
            report["cargo_manifest_sha256"] = hashlib.sha256(cargo).hexdigest()
            report["limitations"] = [
                "Experimental lookup(input) to call named arg argument 1 profile only.",
                "Dependency-free root Cargo crate with one explicit binary only.",
                "Generated Cargo metadata disables build hooks and automatic target discovery.",
                "Dependencies, workspaces, proc macros, cfg and framework coverage unqualified.",
                "Call names do not authenticate Command ownership or prove shell execution.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Trusted Rust toolchain required; Cargo offline is not OS network isolation.",
            ]
        if discovery_profile == "rust-env-shell-v1":
            report["limitations"] = [
                "std::env::var literal key to chained shell command argument profile only.",
                *report["limitations"][1:4],
                *report["limitations"][5:],
                "Chained Command::new literal sh/bash path, arg(-c), arg(value) graph forms only.",
                "Environment attacker control and command execution are not established.",
                "Only bounded receiver wrappers stripped; split builders/args arrays omitted.",
                "Standard-library graph signatures and sanitizer semantics remain unqualified.",
            ]
        if repair_dir is not None:
            report["repair_identity"] = repair_identity
            report["limitations"] = [
                "Experimental Lookup(name) parameter to CommandText assignment profile only.",
                "C# source only; dependencies, builds and other languages omitted.",
                "Syntax facts do not authenticate framework or database types.",
                "Only uniquely mapped paths published; unsupported paths retained in raw output.",
                "Discovery only; no qualified triage, complete coverage or clean verdict.",
                "Trusted tools required; receipt hashes do not authenticate the publisher.",
                "Network not isolated by this command; automatic result reuse disabled.",
            ]
        with store.transaction() as session:
            session.add(ScanAttempt(id=attempt_id, run_id=run_id, created_at=now(), report=report))
        candidates = []
        active_stage = "source_copy"
        try:
            for record in prepared:
                target = source / record.path
                target.parent.mkdir(parents=True, exist_ok=True)
                content = (tree / record.path).read_bytes()
                if hashlib.sha256(content).hexdigest() != record.sha256:
                    raise TraceProofError("Source integrity changed")
                target.write_bytes(content)
            if cargo is not None:
                (source / "Cargo.toml").write_bytes(cargo)
            endpoint_args = []
            endpoint_digest = None
            if discovery_profile in {"python-flask-system-v1", "python-flask-path-v1"}:
                from traceproof.joern_flask import parse_isolated

                audit = []
                shadowed = any(
                    Path(f.path).name in {"flask.py", "os.py"}
                    or "flask" in Path(f.path).parts[:-1]
                    or "os" in Path(f.path).parts[:-1]
                    for f in selected
                )
                for record in selected:
                    facts = (
                        {"status": "local_module_shadow", "sources": [], "sinks": []}
                        if shadowed
                        else parse_isolated(
                            (source / record.path).read_bytes(),
                            **(
                                {"file_paths": True}
                                if discovery_profile == "python-flask-path-v1"
                                else {}
                            ),
                        )
                    )
                    audit.append(
                        dict(
                            facts,
                            file=record.path,
                            absolute_file=str(source / record.path),
                            sha256=record.sha256,
                        )
                    )
                endpoint_path = root / "endpoints.json"
                endpoint_path.write_text(json.dumps(audit, indent=2))
                endpoint_digest = hashlib.sha256(endpoint_path.read_bytes()).hexdigest()
                report["endpoint_audit"] = {
                    "sha256": endpoint_digest,
                    "file_status_counts": dict(Counter(f["status"] for f in audit)),
                }
                endpoint_args = ["--param", f"endpointFile={endpoint_path}"]
            query = root / "query.sc"
            query.write_bytes(
                files("traceproof")
                .joinpath(
                    "queries/joern-java-path.sc"
                    if discovery_profile == "java-spring-file-path-v1"
                    else "queries/joern-rust-env-shell.sc"
                    if discovery_profile == "rust-env-shell-v1"
                    else f"queries/joern-{language}-argv-system.sc"
                    if discovery_profile == "c-family-argv-system-v1"
                    else "queries/joern-go-http-shell.sc"
                    if discovery_profile == "go-http-shell-v1"
                    else f"queries/joern-{language}-express-eval.sc"
                    if discovery_profile == "express-request-eval-v1"
                    else "queries/joern-python-flask-path.sc"
                    if discovery_profile == "python-flask-path-v1"
                    else "queries/joern-python-flask-system.sc"
                    if discovery_profile == "python-flask-system-v1"
                    else f"queries/joern-{language}-flow.sc"
                )
                .read_bytes()
            )
            query_digest = hashlib.sha256(query.read_bytes()).hexdigest()
            report["query_sha256"] = query_digest
            active_stage = "prepare"
            stage(
                frontend
                + [
                    str(source),
                    "--output",
                    str(root / "cpg.bin"),
                ],
                root,
                "prepare",
                extraction_timeout,
                **stage_options,
            )
            active_stage = "analyze"
            stage(
                [
                    str(home / "joern"),
                    "-J-Xmx2g",
                    "--script",
                    str(query),
                    "--param",
                    f"cpgFile={root / 'cpg.bin'}",
                    "--param",
                    f"outFile={root / 'flows.json'}",
                ]
                + endpoint_args,
                root,
                "analyze",
                timeout,
                **stage_options,
            )
            active_stage = "normalize_and_verify"
            verified_source(store, run_id)
            for record in prepared:
                if hashlib.sha256((source / record.path).read_bytes()).hexdigest() != record.sha256:
                    raise TraceProofError("Prepared source changed")
            if (
                endpoint_digest is not None
                and hashlib.sha256(endpoint_path.read_bytes()).hexdigest() != endpoint_digest
            ):
                raise TraceProofError("Endpoint selection changed")
            if cargo is not None and (source / "Cargo.toml").read_bytes() != cargo:
                raise TraceProofError("Prepared Cargo metadata changed")
            if hashlib.sha256(query.read_bytes()).hexdigest() != query_digest:
                raise TraceProofError("Query changed")
            with (root / "flows.json").open("rb") as handle:
                raw = handle.read(MAX_SARIF_BYTES + 1)
            report["native_output_sha256"] = hashlib.sha256(raw).hexdigest()
            doc = decode_output(raw, language, rule)
            coverage = discovery_coverage(doc, source, selected, language)
            if language == "rust" and coverage["represented_rust_files"] == 0:
                report["discovery_coverage"] = coverage
                raise TraceProofError("Rust preparation produced no selected source in graph")
            if repair_dir is not None:
                from traceproof.joern_csharp import map_output, repaired_frontend

                _, after_identity = repaired_frontend(store, home, Path(repair_dir))
                if after_identity != repair_identity:
                    raise TraceProofError("Repair tooling changed during scan")
                raw, mapping = map_output(doc, source, selected)
                (root / "source-mapping.json").write_text(json.dumps(mapping, indent=2))
                report["source_mapping"] = {
                    "validated_paths": mapping["validated_paths"],
                    "unsupported_paths": mapping["unsupported_paths"],
                    "artifact": str(root / "source-mapping.json"),
                }
            sarif = to_sarif(raw, source, manifest, language, rule)
            candidates, summary = normalize(sarif, manifest, tree)
            (root / "results.sarif").write_bytes(sarif)
            report.update(summary, status="partial", sarif_sha256=hashlib.sha256(sarif).hexdigest())
            report.update(
                discovery_coverage=coverage,
                diagnostic_errors=None,
                diagnostic_warnings=None,
                process_stages_completed=True,
            )
        except (TraceProofError, OSError) as exc:
            candidates = []
            report.update(
                status="failed", failure_kind=type(exc).__name__, failed_stage=active_stage
            )
        report["joern_diagnostics"] = observe_logs(root, selected)
        with store.transaction() as session:
            for candidate in candidates:
                session.add(
                    Candidate(
                        id=str(uuid4()),
                        attempt_id=attempt_id,
                        fingerprint=candidate["fingerprint"],
                        evidence=candidate,
                    )
                )
            session.get(ScanAttempt, attempt_id).report = report
        return report
