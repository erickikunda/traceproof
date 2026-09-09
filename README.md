# TraceProof

Evidence-driven, LLM-assisted vulnerability discovery.

**Implemented slice:** local CSV/archive intake with durable SQLite status and verified
source snapshots. **Not yet implemented:** indexing, vulnerability detection, LLM calls,
scan reports, benchmark execution, Git/GCS retrieval, API hosting or OpenShift workers.
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

All results are JSON. Commands fail with a nonzero exit code for request/storage errors.
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
[slice status](docs/development/slice-01.md).
