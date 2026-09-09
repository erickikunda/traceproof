# TraceProof

Evidence-driven, LLM-assisted vulnerability discovery.

**Implemented slices:** local CSV/archive intake, verified source snapshots, resumable
Python syntax indexing, JSON/Markdown coverage reports, and optional CodeQL extraction.
**Not yet implemented:** vulnerability detection, resolved call graphs, LLM calls,
vulnerability reports, benchmark execution, Git/GCS retrieval, API hosting or OpenShift workers.
A `snapshotted` run means source is ready for analysis; it is not a clean security scan.

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). Linux/macOS are supported for
this local slice. CodeQL is not needed for intake.

```bash
uv sync --locked
uv run traceproof init
uv run python examples/create_archive.py --output work/demo
uv run traceproof import-csv work/demo/repos.csv --input-root "$PWD/work/demo" --key demo-1
```

The import result includes `import_id` and per-row `run_id`. Use the actual returned IDs:

```bash
uv run traceproof worker IMPORT_ID
uv run traceproof import-status IMPORT_ID
uv run traceproof run-status RUN_ID
uv run traceproof verify-snapshot SNAPSHOT_ID
```

Results are JSON unless Markdown is requested. Commands fail with a nonzero exit code
for request/storage errors.
Imports and workers can succeed with rejected/failed individual rows: inspect each
row's `state` and `error`. An identical request with the same `--key` returns the existing
import. Reusing a key for different CSV bytes or input root is an error.

Pass the global option before the command to select another local state directory:

```bash
uv run traceproof --state-dir /absolute/local/state init
```

`worker --max-items 1 IMPORT_ID` processes one ready item. Run the worker again to
continue. Only one worker may run against a state directory; the OS releases the lock
on process death. Interrupted items resume automatically, capped at three attempts.
Rejected or failed archives need a corrected input and a new submission key.

## Index and retrieve coverage

Run `traceproof init` again to upgrade an existing Slice 01 database to schema `0002`.
Then use a captured run:

```bash
uv run traceproof index-run RUN_ID
uv run traceproof query-index RUN_ID --kind symbols --limit 100
uv run traceproof query-index RUN_ID --kind calls --path project/app.py
uv run traceproof repo-report REPO_ID
uv run traceproof repo-report REPO_ID --run-id RUN_ID --format markdown > coverage.md
# Optional, requires CodeQL on PATH (verified locally with 2.26.3):
uv run traceproof codeql-extract RUN_ID --timeout 300
uv run traceproof codeql-status ATTEMPT_ID
```

Re-running `index-run` resumes persisted file checkpoints or reuses the completed index
for the same snapshot/parser version. It always verifies source integrity first.
Reports and index queries only read stored results. Repository report retrieval selects
the latest admitted run; it returns an error if that run has no published index rather
than silently falling back. Use `--run-id` to select a historical run.

The report is **index coverage, not a vulnerability verdict**. `finding_count` is null,
and unsupported files, parse errors and unresolved calls remain visible. A `ready`
Python index gate only means all `.py` files parsed and at least one function was found.
Calls are syntactic inventory with snapshot-bound evidence; all targets remain unresolved.
JSON includes per-file rows for dashboard ingestion. See the
[Slice 02 contract and limitations](docs/development/slice-02.md).

CodeQL extraction uses Python `--build-mode=none`, a separate attempt directory, a
restricted environment and a timeout. Inspect its `status`: an unsuccessful extraction
still returns a durable diagnostic record with CLI exit code zero. Extraction success
does not verify coverage or run security queries. Raw logs can contain source and stay
under the local state directory. Provide a disk quota when using this opt-in command;
automatic artifact cleanup and a production container sandbox are not implemented.

## CSV contract

Required columns: `repo_id,source_type,source_uri,owner,classification`.
Optional: `sha256,scan_profile`. No other columns are supported by this first slice.
Use `source_type=pvc` for local `.tar`, `.tar.gz` or `.zip` files; PVC is the future
deployment source type, not a requirement to mount a volume on your laptop.
`source_uri` must be absolute and beneath the provided input root. No symlinks are followed.
`scan_profile` currently accepts `standard`; it records future scan intent only.

The optional `sha256` verifies the original archive bytes. Without an expected digest,
the source is pinned when the worker copies it, not when the CSV is admitted. Producers
must finish writing an archive before submitting it. A changed archive requires a new
submission key if it should create a new run.

Archives preserve their relative directory layout. Root discovery is deferred to indexing.
Nested archives are opaque files, never recursively unpacked. Links, device/special and
sparse files, traversal, ambiguous names, case/Unicode collisions and encrypted ZIPs are
rejected. Size/member/depth/ratio limits are enforced; see `ArchiveLimits` for defaults.

## Local state and security boundary

`.traceproof/traceproof.db` stores metadata and run state. Immutable-by-convention artifact
generations contain the original archive, extracted tree and manifest. Published files
are read-only; verification detects modification. This is not a sandbox against the
owning OS user. State and archives must be trusted local storage accessible only to the
operator; no multi-user authentication or hostile-code execution is provided.

The worker never executes source, build scripts or archive commands. There are no
provider credentials or LLM calls in this slice. Use public/synthetic data on the personal
laptop unless you have explicit authorization for other material. Do not commit runtime
state, credentials or benchmark answers.

An abrupt process death can leave unpublished `.stage-*` directories or a published
artifact without a DB reference. Only manifests referenced by committed records are
accepted results. Published content is verified and safely reused when intake resumes;
automatic orphan retention/cleanup is a later feature.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

SQLite migrations run through `traceproof init` using Alembic. SQLAlchemy domain storage
is the starting point for PostgreSQL, but distributed claims and PostgreSQL integration
are not implemented or certified yet. The local OS lock is deliberately not a substitute
for production heartbeat leases.

See [documentation](docs/README.md), [system design](docs/architecture/system-design.md),
[implementation plan](docs/plans/implementation-plan.md), and
[Slice 01 status](docs/development/slice-01.md) and
[Slice 02 status](docs/development/slice-02.md).
