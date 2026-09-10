# Slice 22: local operator preflight

```bash
uv run traceproof doctor
uv run traceproof doctor --query /absolute/approved.ql
```

`doctor` inspects the supported Python version, recorded SQLite migration versus the
packaged migration head, CodeQL executable availability on PATH, optional query entry
availability/policy and free filesystem bytes. It does not initialize missing state,
apply migrations, invoke CodeQL, compile queries, inspect credentials or contact providers.
SQLite is opened read-only for metadata inspection. This is not a database integrity scan.

Each check reports pass/fail/not_checked/info, explanatory detail and a suggested action.
Any failed prerequisite yields `blocked` and exit code 1. Without a supplied query, an
otherwise successful check yields `incomplete` with exit code 0. With a valid query and
passing prerequisites it yields `preflight_passed`. Scripts must inspect the JSON status.

Executable presence is not execution success. Query dependencies, actual tool version,
filesystem permissions, available quotas and enough capacity for a particular repository
remain runtime checks. Free bytes are informational, with capacity sufficiency unknown.
The command does not grant scan readiness, security coverage or enterprise qualification.

Tests cover missing state without creation, stale schema without migration, unreadable
database, source-tree query rejection, absent CodeQL and CLI error/secret handling. No
schema change is required. This extends local M0 prerequisite diagnostics; it does not
complete environment qualification.
