"""Execution boundary for trusted scanner adapters; no database or triage access.

Input may be a prepared database or source tree, as required by the adapter.
Results describe process execution only, never coverage or vulnerability validity.
Output parsing and evidence qualification remain engine-specific responsibilities.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol


@dataclass(frozen=True)
class ExecutionRequest:
    input_path: Path
    rules_path: Path
    work_dir: Path
    timeout_seconds: int
    threads: int
    ram_mb: int


@dataclass(frozen=True)
class ExecutionResult:
    status: Literal["unavailable", "launch_failed", "timeout", "query_failed", "completed"]
    version: str | None
    exit_code: int | None
    output_path: Path
    log_path: Path


class ScannerExecutor(Protocol):
    def __call__(self, request: ExecutionRequest) -> ExecutionResult: ...
