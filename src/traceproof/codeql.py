"""Opt-in local language-selected extraction diagnostics; no security queries or source builds."""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from traceproof.codeql_resources import resource_settings
from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.java_index import build_java_index
from traceproof.languages import (
    adapter_for,
    select_language,
    validate_extraction_scope,
    validate_selection,
)
from traceproof.persistence import CodeqlAttempt


def extract(
    store,
    run_id,
    timeout=300,
    skip_baseline=False,
    *,
    threads=2,
    ram_mb=2048,
    language="python",
    java_profile="dependency-free",
    allow_csharp_downloads=False,
):
    """Caller holds exclusive_worker; attempts and artifacts are never overwritten."""
    resources = resource_settings(threads, ram_mb)
    validate_selection(language, java_profile)
    if not 1 <= timeout <= 3600:
        raise TraceProofError("Extraction timeout must be between 1 and 3600 seconds")
    run, manifest, tree = verified_source(store, run_id)
    requested_language = language
    language = select_language(manifest, language)
    adapter = adapter_for(language)
    if language == "csharp" and not allow_csharp_downloads:
        raise TraceProofError(
            "C# extraction may download a .NET SDK and NuGet dependencies; "
            "explicit allow-csharp-downloads is required"
        )
    scope = validate_extraction_scope(manifest, language, java_profile)
    scope["language_selection"] = "automatic" if requested_language == "auto" else "explicit"
    if language == "csharp":
        scope["extractor_downloads_allowed"] = True
    if language == "java":
        scope["syntax_index"] = build_java_index(store, run_id)
    attempt_id = str(uuid4())
    root = store.root / "codeql" / attempt_id
    root.mkdir(parents=True, mode=0o700)
    extraction_tree = tree
    copy_suffix = ".cs" if language == "csharp" else ".java"
    if language == "csharp" or (language == "java" and java_profile == "source-only"):
        extraction_tree = root / "source"
        extraction_tree.mkdir(mode=0o700)
        for file in manifest.files:
            if not file.path.lower().endswith(copy_suffix):
                continue
            target = extraction_tree / file.path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(tree / file.path, target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != file.sha256:
                raise TraceProofError("Source extraction copy failed integrity verification")
    executable = shutil.which("codeql")
    result = {
        "schema_version": "1",
        "attempt_id": attempt_id,
        "created_at": datetime.now(UTC).isoformat(),
        "run_id": run.id,
        "snapshot_id": manifest.snapshot_id,
        "status": "running",
        "security_analysis_performed": False,
        "coverage_verified": False,
        "database_path": str(root / "database"),
        "timeout_seconds": timeout,
        "requested_resources": resources,
        "build_mode": "none",
        "language": language,
        "language_scope": scope,
        "baseline_requested": not skip_baseline,
    }
    with store.transaction() as session:
        for prior in session.scalars(select(CodeqlAttempt).where(CodeqlAttempt.run_id == run_id)):
            if prior.result["status"] == "running":
                prior.result = {**prior.result, "status": "interrupted"}
        session.add(CodeqlAttempt(id=attempt_id, run_id=run_id, result=result))
    started = time.monotonic()
    if executable is None:
        result["status"] = "unavailable"
    else:
        # Do not forward API keys, proxy credentials, PYTHONPATH or CodeQL overrides.
        env = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(root),
            "TMPDIR": str(root),
            "LANG": "en_US.UTF-8",
        }
        try:
            version = subprocess.run(
                [executable, "version", "--format=json"],
                env=env,
                cwd=root,
                capture_output=True,
                timeout=10,
                check=True,
            )
            result["codeql_version"] = json.loads(version.stdout)["version"]
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            result["codeql_version"] = "unknown"
        command = [
            executable,
            "database",
            "create",
            str(root / "database"),
            f"--language={adapter.extractor}",
            "--build-mode=none",
            f"--source-root={extraction_tree}",
            f"--threads={threads}",
            f"--ram={ram_mb}",
            f"--common-caches={root / 'cache'}",
        ]
        if skip_baseline:
            command.append("--no-calculate-baseline")
        # Raw extractor output can contain source and remains in protected local artifacts.
        # This POC requires an operator-controlled disk quota for the whole state directory.
        with (root / "extract.log").open("wb") as log:
            try:
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
                    result.update(status="extracted" if code == 0 else "failed", exit_code=code)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    result["status"] = "timeout"
            except OSError:
                result["status"] = "launch_failed"
        try:
            verified_source(store, run_id)
            if extraction_tree != tree:
                for file in manifest.files:
                    if file.path.lower().endswith(copy_suffix):
                        target = extraction_tree / file.path
                        if (
                            target.is_symlink()
                            or hashlib.sha256(target.read_bytes()).hexdigest() != file.sha256
                        ):
                            raise TraceProofError("Source extraction copy changed")
        except (TraceProofError, OSError):
            result["status"] = "integrity_failed"
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    with store.transaction() as session:
        session.get(CodeqlAttempt, attempt_id).result = result
    return result


def extraction_status(store, attempt_id):
    with store.transaction() as session:
        attempt = session.get(CodeqlAttempt, attempt_id)
        if attempt is None:
            raise TraceProofError("CodeQL extraction attempt not found")
        return attempt.result
