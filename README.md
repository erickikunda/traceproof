# TraceProof

Evidence-driven, LLM-assisted vulnerability discovery.

For step-by-step use, report interpretation and recovery, read the
[CLI user/operator guide](docs/guides/cli-operator-guide.md).

Use `run-history REPO_ID` and `scan-history REPO_ID` to find previous work, including
failed or unpublished scans. Both support `--offset` and `--limit`; scan history also
accepts `--run-id`. See [Slice 16](docs/development/slice-16.md).

**Implemented slices:** local CSV/archive intake, verified source snapshots, resumable
Python indexing, conservative call candidates, bounded evidence bundles, CodeQL security
queries, advisory triage with replay/opt-in OpenAI and Anthropic adapters, source claim checks,
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

Run `traceproof init` again to upgrade an existing database to schema `0006`.
Then use a captured run:

```bash
uv run traceproof index-run RUN_ID
uv run traceproof query-index RUN_ID --kind symbols --limit 100
uv run traceproof query-index RUN_ID --kind calls --path project/app.py
uv run traceproof repo-report REPO_ID
uv run traceproof repo-report REPO_ID --run-id RUN_ID --format markdown > coverage.md
# Optional, requires CodeQL on PATH (verified locally with 2.27.0):
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

Slice 06 recognizes retained Flask `request` import prefixes when complete file evidence
fits within those same bounds and no syntactic rebinding is found. Rebuild bundles to
builder version 3 for file line counts. The gate records its source mapping explicitly;
unrecognized or incomplete patterns still abstain. This supports review, not automatic
confirmation or dismissal. See [Slice 06](docs/development/slice-06.md).

## Published repository reports

Slice 07 combines one scan attempt and its advisory history into an immutable summary.
Run `init` to apply the latest migration, then:

```bash
uv run traceproof publish-report REPO_ID
uv run traceproof report-history REPO_ID
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format html > report.html
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format markdown > report.md
uv run traceproof get-report REPO_ID --report-id REPORT_ID > report.json
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format scan-csv > scan.csv
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format candidates-csv > candidates.csv
```

Publishing reads stored state without source access or model calls. Identical state
reuses its report; later decisions create a new version. Use `--run-id` and `--attempt-id`
on publication for historical scans. Exact report retrieval enforces repository ownership.
Without an ID, retrieval selects the latest published version of the latest admitted run
and refuses to hide a newer analysis attempt behind an older report.

Reports show unreviewed candidates, replay/live status and unknown coverage. Default
summaries omit source excerpts, model prose and raw diagnostics. Paths, rules, metadata
and identifiers can still be sensitive: share within the authorized audience. CSV has
separate scan and candidate grains, joined by `report_id`; use the scan export even when
there are no candidates. See [Slice 07 contract](docs/development/slice-07.md).

Compare two exact published versions without rerunning analysis:

```bash
uv run traceproof compare-reports REPO_ID BASELINE_REPORT_ID CURRENT_REPORT_ID
uv run traceproof compare-reports REPO_ID BASELINE_REPORT_ID CURRENT_REPORT_ID --format markdown
```

Slice 08 distinguishes exact repeated observations, tentative unchanged-file matches,
ambiguous groups and observations present on only one side. Absence never means fixed.
Unknown or different analysis scope disables tentative matching. See
[Slice 08](docs/development/slice-08.md) and the
[implementation progress assessment](docs/development/progress.md).

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

## Operator review history

Slice 12 adds explicit operator assertions against a candidate's exact evidence bundle.
Run `init` for migration 0006. Save a review request JSON, then:

```bash
uv run traceproof review-history REPO_ID ATTEMPT_ID CANDIDATE_FINGERPRINT
uv run traceproof record-review REPO_ID ATTEMPT_ID CANDIDATE_FINGERPRINT /absolute/review.json REVIEW_KEY
uv run traceproof publish-report REPO_ID
```

Requests contain `reviewer_label`, `state` (`confirmed`, `false_positive`, `needs_review`,
or `deferred`), `rationale`, `bundle_id`, `evidence_ids`, and `expected_revision` (initially
zero). Use the current revision from history for the next review. Retrying the same key
and request returns the original entry; stale or conflicting writes fail.

Review history is append-only. Raw candidates stay visible and unchanged; reports show
operator review separately from model advice. Reviewer identity is self-declared, and
these assertions do not set independent verification or benchmark precision. Summary
exports omit reviewer labels and notes; the explicit history command includes them.
See [Slice 12 contract](docs/development/slice-12.md).

Anthropic Messages is also available through an explicit `provider: "anthropic"` model policy. Configure the approved endpoint, model, pricing and `api_key_env` explicitly; all live transmission remains opt-in. See [Slice 13 contract](docs/development/slice-13.md) for setup and accounting limits.

Use `traceproof resolve-report REPO_ID --selection latest-completed` to retrieve the latest published static review-ready report together with disclosure of newer work. The default `latest-attempt` mode never falls back. See [Slice 14 contract](docs/development/slice-14.md) for freshness semantics and JSON fields.

## Benchmark contract preparation

Slice 10 validates separate repository manifests and evaluator-only labels. It does not
run the benchmark or calculate quality metrics:

```bash
uv run traceproof benchmark-schema > benchmark-schemas.json
uv run traceproof benchmark-check examples/benchmark-manifest.json
uv run traceproof benchmark-check examples/benchmark-manifest.json --labels examples/benchmark-labels.json
# Optional alignment against snapshots already stored in the selected state directory:
uv run traceproof benchmark-check /absolute/manifest.json --labels /absolute/labels.json --check-local-snapshots
```

Examples use synthetic placeholder digests; they pass contract checks but intentionally
cannot align to real local snapshots. The manifest-only command returns its canonical
digest for the label file's `manifest_sha256`. Keep both files outside analyzed archives;
labels must never be submitted through CSV intake or sent to models. See
[Slice 10 contract and limits](docs/development/slice-10.md).

Slice 11 adds an offline scorecard over exact stored reports:

```bash
uv run traceproof benchmark-evaluate /absolute/manifest.json /absolute/labels.json /absolute/evaluation-plan.json
uv run traceproof benchmark-evaluate /absolute/manifest.json /absolute/labels.json /absolute/evaluation-plan.json --format markdown
```

The plan pins the manifest, query digest, CodeQL version, profile, supported rules and
one report ID per selected repository. `benchmark-schema` includes its schema. Missing
reports remain explicit cases. Scores measure provisional candidate-location matches;
precision and confirmed recall remain unknown. No scans or model calls are dispatched.
See [Slice 11 scope and score interpretation](docs/development/slice-11.md).

The evaluator also supports `--format summary-csv`, `repositories-csv`, `labels-csv`
and `candidates-csv` for dashboard ingestion. Keep the summary and join details using the
scorecard identity. See [Slice 17 CSV contracts](docs/development/slice-17.md).

Evaluator version 2 adds per-CWE proxy metrics in JSON, Markdown and
`--format weaknesses-csv`. Classes without labels remain unknown, and missing evaluations
stay in denominators. See [Slice 18](docs/development/slice-18.md).

## Development

Run the real CodeQL acceptance suite with an approved local `CodeInjection.ql` entry:

```bash
uv run traceproof acceptance-run work/acceptance-001 /absolute/CodeInjection.ql --timeout 300
```

The output directory must be new. The runner creates its own SQLite state and synthetic
vulnerable/fixed/incomplete archives, publishes reports in all five formats, and writes
`acceptance.json`. It uses no model calls, performs no query downloads, and exits nonzero
when assertions fail. The incomplete fixture deliberately skips CodeQL after its Python
index is blocked. This explicit gate applies to the acceptance runner; individual
operator commands remain separately callable.

Published reports now include `static_review_readiness`, which joins the current Python
index and static-analysis diagnostics. `ready_for_review` is not verified coverage,
adjudication or a clean security verdict. Historical reports without that field show
unknown readiness; republish to capture current stored index state. See
[Slice 09](docs/development/slice-09.md).

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
