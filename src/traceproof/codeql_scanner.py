"""CodeQL process adapter. Source verification and publication belong to the caller."""

import json
import os
import shutil
import signal
import subprocess

from traceproof.scanner import ExecutionRequest, ExecutionResult


def execute(request: ExecutionRequest) -> ExecutionResult:
    """Execute approved local rules against a prepared database, without downloads."""
    root = request.work_dir
    report = {}
    executable = shutil.which("codeql")
    if executable is None:
        report["status"] = "unavailable"
    else:
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
            report["version"] = json.loads(version.stdout)["version"]
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            report["version"] = "unknown"
        command = [
            executable,
            "database",
            "analyze",
            str(request.input_path),
            "path:" + str(request.rules_path),
            "--format=sarifv2.1.0",
            "--no-download",
            "--no-sarif-add-file-contents",
            "--no-sarif-add-snippets",
            f"--output={root / 'results.sarif'}",
            f"--threads={request.threads}",
            f"--ram={request.ram_mb}",
            f"--common-caches={root / 'cache'}",
        ]
        with (root / "analyze.log").open("wb") as log:
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
                    code = process.wait(timeout=request.timeout_seconds)
                    report.update(exit_code=code, status="query_failed" if code else "completed")
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    report["status"] = "timeout"
            except OSError:
                report["status"] = "launch_failed"
    return ExecutionResult(
        status=report["status"],
        version=report.get("version"),
        exit_code=report.get("exit_code"),
        output_path=root / "results.sarif",
        log_path=root / "analyze.log",
    )
