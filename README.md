# TraceProof

Evidence-driven, LLM-assisted vulnerability discovery.

**Implemented slices:** local CSV/archive intake, verified source snapshots, resumable
Python indexing, conservative call candidates, bounded evidence bundles, CodeQL security
queries, advisory triage with replay/opt-in OpenAI adapters, source claim checks,
bounded context expansion, cost reservations, and reports.
**Not yet implemented:** verified vulnerability adjudication, proven reachability,
benchmark execution, Git/GCS retrieval, API hosting or OpenShift workers.
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

Run `traceproof init` again to upgrade an existing database to schema `0004`.
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

## Source evidence and security-query candidates

Re-run `index-run` to build the v2 index required by `call-context`. Old indexes are
retained; retrieve an old coverage report with `repo-report --run-id RUN_ID --index-id INDEX_ID`.

```bash
uv run traceproof call-context RUN_ID project/app.py --module-root project
uv run traceproof source-evidence RUN_ID project/app.py 1 20
uv run traceproof codeql-analyze EXTRACTION_ID /absolute/approved/query.ql --timeout 600
uv run traceproof scan-report REPO_ID
uv run traceproof scan-report REPO_ID --run-id RUN_ID --attempt-id ATTEMPT_ID --format markdown
```

The call-context view adds conservative candidates for direct top-level functions and
absolute imports under an explicit module root. Shadowing, ambiguous modules, decorators
and dynamic behavior leave gaps. `static_candidate` never means proven reachability.
Evidence reads verify digests and reject ranges over 200 lines or 32 KiB; add `--sha256`
to require a previously returned evidence digest.

`codeql-analyze` accepts an operator-controlled local `.ql` or `.qls` entry, uses
`--no-download`, and atomically publishes unreviewed candidates with diagnostics.
Install approved query packs separately. For a personal-laptop synthetic test, this
version was exercised:

```bash
codeql pack download codeql/python-queries@1.8.10 --dir=work/codeql-packs --common-caches=work/codeql-download-cache
# Pass this local query to codeql-analyze:
# work/codeql-packs/codeql/python-queries/1.8.10/Security/CWE-094/CodeInjection.ql
```

Inspect `status` even when the command exits zero: timeouts, failed queries and invalid
SARIF are durable reports. Zero candidates is not a clean verdict. Reports select the
latest admitted run/latest attempt without falling back to earlier successes. Raw SARIF
and logs remain in protected state storage; report text can contain sensitive tool output.

The original CodeQL installation's `scc` hang was resolved by reinstalling the official
GitHub 2.27.0 bundle. Normal extraction now works with baseline counting enabled.
`--skip-baseline` remains an optional diagnostic fallback and records the omitted baseline.
See [Slice 03 status](docs/development/slice-03.md) for the tested scope and limitations.

## Evidence bundles and advisory triage

Use an attempt ID and candidate fingerprint from `scan-report`:

```bash
uv run traceproof build-bundle ATTEMPT_ID CANDIDATE_FINGERPRINT
uv run traceproof bundle-status BUNDLE_ID
uv run traceproof triage-budget RUN_ID 100000
uv run traceproof triage BUNDLE_ID examples/triage-replay-config.json demo-triage-1 \
  --replay examples/triage-replay-response.json
uv run traceproof triage-report RUN_ID
```

The example is entirely offline. It uses fictional usage/rates to test the cost ledger,
and returns an explicit abstention. `100000` micro-USD is a $0.10 accounting cap; no money
is spent by replay. A run budget is fixed once configured. Reusing a triage key with the
same bundle/config/fixture retrieves its result without another invocation.

Bundles include primary, flow and related locations, capped at eight locations, 16 KiB
of source and a 32 KiB envelope. Gaps remain visible; partial bundles skip model invocation.
Triage decisions are advisory (`needs_review`, `likely_false_positive`, `abstain`) and
never suppress or confirm a candidate. Invalid citations/refusals/incomplete outputs
abstain. Missing usage, interrupted calls and ambiguous failures retain the reservation.

The live OpenAI Responses adapter requires an operator-authored configuration with the
approved HTTPS endpoint/host, model ID, allowed classifications, explicit source-transmission
opt-in, pricing, and a named API-key environment variable. There is no built-in model choice
or price. Live network behavior is tested with mocks; **no live provider call was made**.
See [Slice 04 configuration and limits](docs/development/slice-04.md).

Slice 05 adds quoted source/sink/flow/guard claims for `py/code-injection` and
`py/command-line-injection`. Failed claims abstain; unsupported rules skip the provider.
Checks establish narrow syntax and retained flow consistency, not vulnerability truth.
Rebuild old bundles for flow metadata, and use a new triage key for the updated prompt.

```bash
uv run traceproof evidence-policy py/code-injection
uv run traceproof check-evidence BUNDLE_ID /absolute/decision.json
uv run traceproof expand-bundle BUNDLE_ID /absolute/expansion.json
```

Expansion requests are JSON arrays of `path`, `line`, `end_line`, and `reason` objects.
They create immutable child bundles with at most four requested ranges per step and two
steps, within the original total source/envelope caps. Expansion never calls a provider;
triage of a child requires an explicit new request and uses the same run budget.
See [Slice 05 behavior and limitations](docs/development/slice-05.md).

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

The intake/index workers never execute source or build scripts. Offline replay requires
no provider credentials; live triage requires explicit configuration. Use public/synthetic data on the personal
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
See [Slice 03 status](docs/development/slice-03.md) for static analysis and the current
[Slice 04 status](docs/development/slice-04.md) for evidence bundles and triage.
