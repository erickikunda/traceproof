# Slice 02 — Python inventory and coverage

This slice turns a captured repository into a durable syntax inventory and a shareable
coverage report. It is the first part of M2: Python indexing, the parsing health gate,
evidence references and optional CodeQL extraction diagnostics. M2 is not complete.

## User workflow

1. Upgrade storage with `veriflow init`; existing intake runs and snapshots survive.
2. Run `veriflow index-run RUN_ID` against a captured snapshot.
3. Inspect `query-index RUN_ID --kind symbols` or `--kind calls`.
4. Retrieve `repo-report REPO_ID`, optionally with `--run-id RUN_ID` or `--format markdown`.
5. Optionally run `codeql-extract RUN_ID` and retrieve `codeql-status ATTEMPT_ID` later.

```mermaid
sequenceDiagram
    actor Operator
    participant CLI
    participant Artifacts as Verified snapshot
    participant Parser as Isolated AST subprocess
    participant DB as SQLite
    Operator->>CLI: index-run(run)
    CLI->>Artifacts: Verify archive, tree and DB manifest
    CLI->>DB: Create/reuse versioned index
    loop Each file without a checkpoint
        CLI->>Parser: Bounded source bytes (.py only)
        Parser-->>CLI: Symbols, calls, parsing status
        CLI->>DB: Commit file checkpoint
    end
    CLI->>Artifacts: Verify again
    CLI->>DB: Atomically publish coverage report
    Operator->>CLI: repo-report(repo, optional run)
    CLI->>DB: Read materialized report
    CLI-->>Operator: JSON or Markdown; security NOT ASSESSED
```

## Implemented contract

- Functions, async functions, nested definitions and classes include lexical names and
  line ranges. Calls include syntactic expressions, calling lexical scope and location.
  Decorator/default/base expressions are assigned to their enclosing scope. Lambda
  bodies receive a synthetic scope; comprehensions do not receive a separate scope yet.
- Every query result includes an `evidence` object: `snapshot_id`, `path`, `sha256`,
  `line`, `end_line`. Line numbers are one-based and inclusive; call `column` is a
  zero-based UTF-8 byte offset as supplied by Python AST. Source text is not in reports.
- All calls have `resolution=unresolved`. This slice deliberately publishes no resolved
  call edges. Direct-name, cross-module, alias and dynamic dispatch resolution require
  a later tested resolver; no absence of an edge is evidence of unreachability.
- Index identity is `(snapshot_id, indexer version including exact Python version)`.
  Same-snapshot retries resume committed files. Different snapshots are indexed separately;
  cross-snapshot content caching is deferred. Queries only see published indexes.
- JSON report `schema_version=1`, `report_kind=index_coverage` includes run/repository/
  snapshot/index identity, classification, file counts, parsing fraction, function/call
  counts, per-file statuses and limitations. `security_verdict=not_assessed`,
  `security_analysis_performed=false`, `finding_count=null` are explicit invariants.
- `python_index_gate=ready` requires at least one Python file, every `.py` file parsed,
  and at least one function. Otherwise it is `blocked`. Other files are `not_supported`
  and excluded from the Python denominator, never represented as analyzed. This is not
  a repository security coverage gate. Empty denominators have a null fraction.
- File statuses: `parsed`, `not_supported`, `size_limit`, `node_limit`, `parse_error`,
  `resource_limit`, `parser_failed`, `timeout`. Partial coverage reports remain retrievable.
- `run-status.state` retains the intake lifecycle. Added `index_status` and
  `coverage_report_status` describe the separate stage; vulnerability `report_status`
  remains `not_available`.
- Repository retrieval selects the latest admitted run without falling back to older
  successes. Historical selection requires a matching repository/run. Queries and reports
  use the current parser version; migration/selection of earlier parser-version indexes
  will be needed when introducing a new indexer version.

## Bounds and enterprise implications

The local exclusive worker lock covers intake, indexing and CodeQL extraction. SQLite
checkpoints are committed per file; report publication is a single transaction. A process
death before publication leaves an unreadable building generation that resumes on retry.
Expected parser failures become durable gaps; fixing source requires a new snapshot.
Transient failed-file retries within a published generation are not implemented.

The AST worker receives at most 1 MiB per file, accepts at most 50,000 AST nodes, runs
with a 5-second CPU limit and a 10-second parent timeout, and never imports source.
Linux additionally enforces a 512 MiB address-space limit. macOS does not reliably
support that limit; use container memory limits for hostile-input production workloads.
Each file launches a subprocess, favoring isolation for this POC; a bounded reusable
worker pool and representative throughput measurements precede scale-out.

Report aggregation streams file records without retaining all symbols/calls. Queries
are paginated to at most 1,000 entries, but scan the stored JSON inventory to compute
totals. Normalized symbol/edge tables and indexed lookups will be required at production
scale. No evidence supports a 1,000-repository/day claim from this slice.

CodeQL attempts have unique directories, durable running/final status, CLI version,
elapsed time, exit code where available, and private logs. Commands use `shell=False`,
explicit Python language, `--build-mode=none`, two threads and a 2 GiB RAM hint. A timeout
kills the process group. Secrets and extractor overrides are not forwarded; operator PATH
is retained to discover required executables. This is not a network or filesystem sandbox.
The CLI version probe has a separate 10-second timeout. `coverage_verified=false` remains
true of the contract even when status is `extracted`; query-based diagnostics come later.

The local operator must manage disk quotas and retention. Abrupt parent death can leave
an extraction process/artifacts behind; the next attempt marks a previous running record
interrupted but does not locate or kill orphan processes. Before retrying after such a
death, stop the orphan locally. OpenShift Jobs with pod resource/network limits will own
this lifecycle in production. Snapshot storage is immutable by convention, not a hostile
local-user boundary. No bank code or credentials are needed for these synthetic tests.

## Validation and next work

Verified locally: **74 tests passed**, Ruff lint/format checks passed, and wheel/source
distributions built successfully. CodeQL **2.26.3** completed the synthetic one-file
Python extraction with exit code 0 in approximately 2.7 seconds. That fixture is a
functional smoke check, not a throughput benchmark. The test suite's one warning comes
from the intentional duplicate-path ZIP rejection fixture inherited from Slice 01.

Automated tests cover upgrade from schema 0001 with an existing run, nested/async syntax,
encoding and syntax failures, limits, evidence references, source non-execution, idempotent
reuse, actual process-death checkpoint recovery, tampering, coverage gates, historical
retrieval and the CLI. CodeQL fixtures cover missing executable, nonzero exit, success,
timeout and environment filtering. A real synthetic extraction is also exercised locally.

Next: conservative direct/import call resolution with explicit uncertainty, CodeQL
security query/SARIF diagnostics, and evidence-body retrieval. Then bounded model triage,
finding adjudication and vulnerability reports. The 50-repository benchmark labels remain
outside scan inputs; evaluation and threshold tuning are still deferred.
