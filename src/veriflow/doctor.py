"""Read-only local preflight; presence checks are not runtime qualification."""

import shutil
import sqlite3
import sys
from importlib.resources import files

from alembic.config import Config
from alembic.script import ScriptDirectory

from veriflow.domain import VeriFlowError
from veriflow.scanning import query_entry


def diagnose(store, query=None):
    checks = []

    def add(name, status, detail, action=None):
        checks.append({"check": name, "status": status, "detail": detail, "action": action})

    python_ok = (3, 12) <= sys.version_info[:2] < (3, 15)
    add(
        "python",
        "pass" if python_ok else "fail",
        ".".join(map(str, sys.version_info[:3])),
        None if python_ok else "Use the project's supported Python version and locked environment",
    )
    config = Config()
    config.set_main_option("script_location", str(files("veriflow") / "migrations"))
    expected = ScriptDirectory.from_config(config).get_current_head()
    actual = None
    if not store.database.is_file():
        add(
            "database",
            "fail",
            "State database does not exist",
            "Run veriflow init with this --state-dir",
        )
    else:
        try:
            uri = store.database.as_uri() + "?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=1) as connection:
                versions = connection.execute("SELECT version_num FROM alembic_version").fetchall()
            actual = versions[0][0] if len(versions) == 1 else None
            add(
                "database",
                "pass" if actual == expected else "fail",
                f"Recorded schema {actual}; required schema {expected}",
                None
                if actual == expected
                else "Back up and quiesce writers, then run veriflow init",
            )
        except sqlite3.Error:
            add(
                "database",
                "fail",
                "Cannot read schema metadata",
                "Check state directory, access and database health; preserve existing data",
            )
    executable = shutil.which("codeql")
    add(
        "codeql",
        "pass" if executable else "fail",
        "Executable found on PATH; not invoked" if executable else "No executable found on PATH",
        None
        if executable
        else "Install the approved CodeQL bundle and expose its executable on PATH",
    )
    if query is None:
        add(
            "query",
            "not_checked",
            "No query entry supplied",
            "Pass --query with an approved local .ql or .qls file",
        )
    else:
        try:
            entry = query_entry(store, query)
            with entry.open("rb") as handle:
                handle.read(1)
            add(
                "query",
                "pass",
                "Operator query entry exists and is readable; dependencies not checked",
            )
        except (OSError, VeriFlowError):
            add(
                "query",
                "fail",
                "Query entry is unavailable or outside the supported operator-query policy",
                "Use a readable .ql/.qls file outside scanned artifacts; "
                "install approved dependencies separately",
            )
    existing = store.root
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    try:
        free = shutil.disk_usage(existing).free
        add(
            "disk",
            "info",
            {"free_bytes": free, "capacity_sufficient": None},
            "Provision a quota and capacity for source, CodeQL databases and logs; "
            "no universal threshold is asserted",
        )
    except OSError:
        add(
            "disk",
            "not_checked",
            "Free capacity unavailable",
            "Check the selected state filesystem",
        )
    return {
        "schema_version": "1",
        "status": "blocked"
        if any(c["status"] == "fail" for c in checks)
        else "incomplete"
        if query is None
        else "preflight_passed",
        "required_database_schema": expected,
        "recorded_database_schema": actual,
        "checks": checks,
        "limitations": [
            "No CodeQL execution, query compilation, model calls or network probes were performed.",
            "Filesystem permissions, query dependencies and capacity require runtime verification.",
            "Passing preflight does not establish scan readiness or enterprise qualification.",
        ],
    }
