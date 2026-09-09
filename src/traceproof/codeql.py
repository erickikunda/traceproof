"""Opt-in local Python extraction diagnostics; no security queries or source builds."""

import json
import os
import shutil
import signal
import subprocess
import time
from uuid import uuid4

from sqlalchemy import select

from traceproof.domain import TraceProofError
from traceproof.indexing import verified_source
from traceproof.persistence import CodeqlAttempt


def extract(store, run_id, timeout=300):
    """Caller holds exclusive_worker; attempts and artifacts are never overwritten."""
    if not 1 <= timeout <= 3600:
        raise TraceProofError("Extraction timeout must be between 1 and 3600 seconds")
    run, manifest, tree = verified_source(store, run_id)
    attempt_id = str(uuid4())
    root = store.root / "codeql" / attempt_id
    root.mkdir(parents=True, mode=0o700)
    executable = shutil.which("codeql")
    result = {
        "schema_version": "1",
        "attempt_id": attempt_id,
        "run_id": run.id,
        "snapshot_id": manifest.snapshot_id,
        "status": "running",
        "security_analysis_performed": False,
        "coverage_verified": False,
        "database_path": str(root / "database"),
        "timeout_seconds": timeout,
        "build_mode": "none",
        "language": "python",
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
            "--language=python",
            "--build-mode=none",
            f"--source-root={tree}",
            "--threads=2",
            "--ram=2048",
            f"--common-caches={root / 'cache'}",
        ]
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
        except TraceProofError:
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
