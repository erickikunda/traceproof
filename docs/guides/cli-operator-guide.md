# TraceProof CLI user and operator guide

**Scope:** laptop POC through Slice 46, SQLite schema 0009. Commands are run from the repository checkout on Linux/macOS using Python 3.12+. This guide describes implemented behavior. Git/GCS acquisition, HTTP API hosting, distributed workers, authenticated reviewers and OpenShift deployment are future work.

## Evidence gate version 3

The gate now recognizes conservative Flask request aliases, such as
`from flask import request as req`, in supported retained import-to-sink flows. Complete
file context and a non-rebound binding are required. Missing context or ambiguous/shadowed
aliases remain unsupported; passing means supported for review, not a verified vulnerability.

Old triage results remain unchanged. Gate version is part of request identity, so an old
key may conflict after this upgrade. Use `check-evidence BUNDLE_ID DECISION_JSON` for a
local recheck. Requesting new model advice requires a deliberately new key and consumes
the existing run budget/request allowance. It is not an automatic retry of old uncertain
calls. See [Slice 36](../development/slice-36.md) for exact limitations.

## Inspect retained storage

```bash
uv run traceproof storage-audit --max-entries 1000 --max-nodes 100000
```

Run while workers are idle. The command takes the worker lock and reports artifact IDs,
database-reference status and bounded logical file sizes for snapshots, extraction and
scan directories. It never deletes artifacts. Unreferenced or staging entries need review:
they may be useful for recovery. Do not interpret them as safe deletion candidates.

Check `status` and `issues`; limits or unreadable/linked entries make the result incomplete.
Counts exclude database/WAL/backups and are not allocated disk usage. There is no content
integrity check or search for missing directories. The audit may create the worker lock
file but does not modify stored results. See [Slice 35](../development/slice-35.md).

## Find a CodeQL extraction attempt

```bash
uv run traceproof extraction-history REPO_ID --limit 20
uv run traceproof extraction-history REPO_ID --run-id RUN_ID
uv run traceproof codeql-status EXTRACTION_ATTEMPT_ID
```

Use this history when extraction failed before a query attempt existed, or when you lost
the extraction ID. Query attempts remain in `scan-history`. Extraction history shows
recorded status, timing, version and resource settings; it neither starts work nor probes
process liveness. A stored successful result does not verify retained database files.

New records have creation timestamps. Legacy timestamps are null; dated attempts sort
first within each run, followed by undated IDs in descending order. Runs are grouped newest
first. Default limit is 100, maximum 1000; follow `next_offset` with `--offset`. Use exact
IDs for further actions. See [Slice 34](../development/slice-34.md).

## Find a previous import

```bash
uv run traceproof import-history --limit 20
uv run traceproof import-history --state paused --limit 20
uv run traceproof status IMPORT_ID
uv run traceproof import-control-status IMPORT_ID
uv run traceproof import-reports IMPORT_ID
```

History returns newest batches first with their IDs, latest dispatch state/revision and
intake counts. Optional filters are active, paused and cancelled. Follow `next_offset` using
`--offset`; default limit is 100, maximum 1000. Control changes or new imports can shift
later pages. Intake counts do not describe scan completion or findings. Cancelled batches
can retain unstarted rows, and active batches may already have completed intake.
See [Slice 33](../development/slice-33.md) for the projection contract.

## Cancel remaining import dispatch

```bash
uv run traceproof import-control-status IMPORT_ID
uv run traceproof import-control IMPORT_ID cancelled cancel-1 "No longer needed" --expected-revision 0
```

Use the revision returned by status. Cancellation is terminal for this import: it cannot
be resumed. Use pause when you intend to continue later. Already-started rows may finish;
completed work and report retrieval are preserved. `scan-import` reports cancelled with
no continuation offset when it observes the stop. `--rescan` cannot bypass it.

Explicit single-run operations and triage remain available; this cancels import dispatch,
not running processes. If replacement work is needed, explicitly submit a new import with
a new idempotency key. Repeating the original submission key returns the cancelled import.
Keep using this or a newer application version once cancellations exist. No migration beyond
0009 is needed. See [Slice 32](../development/slice-32.md).

## Pause and resume import dispatch

With writers quiesced, apply migration 0009 using `traceproof init`. Existing imports
remain active at revision 0. Then use the revision returned by status:

```bash
uv run traceproof import-control-status IMPORT_ID
uv run traceproof import-control IMPORT_ID paused pause-1 "Maintenance" --expected-revision 0
uv run traceproof import-control IMPORT_ID active resume-1 "Ready" --expected-revision 1
uv run traceproof worker IMPORT_ID
```

A pause takes effect at the next intake or batch-scan row boundary. Work already admitted
at a boundary may finish; no tool process is killed. `status IMPORT_ID` shows dispatch
state separately from row states. `scan-import` returns `dispatch_status: paused` and
`next_offset` for the next row. After resuming, invoke the worker or scan command again;
resume does not launch work. Existing snapshots/reports stay available.

Repeat an identical request key to recover from an uncertain response. A stale revision
or changed request with the same key is rejected; inspect current status before retrying.
History records reasons and revisions, with `--offset`/`--limit` pagination. This is a local
operator control, not authenticated approval. Explicit single-run commands and triage are
not blocked by import pause. See [Slice 31](../development/slice-31.md) for the full scope.

## Triage a candidate page

For synthetic local Ollama testing, with an approved model configuration:

```bash
uv run traceproof triage-budget RUN_ID 0 --max-requests 20
uv run traceproof triage-attempt REPO_ID ATTEMPT_ID examples/triage-ollama-config.json local-pass-1 --limit 5
uv run traceproof triage-report RUN_ID
uv run traceproof publish-report REPO_ID --run-id RUN_ID --attempt-id ATTEMPT_ID
```

The zero monetary budget above is for zero-priced local inference; priced models require
a suitable monetary cap and explicit source-transmission policy. Existing budgets remain
fixed. Replay policies require `--replay RESPONSE_JSON`; a shared replay fixture does not
measure candidate-specific detection quality.

Selection is from the exact attempt in fingerprint order. Default limit is 1, maximum 100.
Repeat the same key/configuration to reuse recorded calls. A new key can cause additional
calls and spend; batch keys do not deduplicate unrelated manual triage calls. Inspect JSON
`status` and the ledger after each page. Budget exhaustion, uncertain provider outcomes
and application errors halt processing. `next_offset` advances past recorded outcomes,
but stays on an application-error candidate. Do not treat a halted page as a successful
triage pass. `page_complete` describes only the selected page. Later publication is explicit.
See [Slice 30](../development/slice-30.md) for retry and stop semantics.

## Share a benchmark scorecard

```bash
uv run traceproof benchmark-history DATASET_ID
uv run traceproof benchmark-get DATASET_ID SCORECARD_ID --format html > scorecard.html
```

Open the exported HTML in a browser. It requires no server, JavaScript or external assets.
The top-level metric is a provisional candidate-location recall proxy, not confirmed recall.
Check evaluation completion and repository scope gaps before interpreting it. Precision
and confirmed recall remain unknown. Expand label/candidate details and provenance as
needed, and expand them before printing. Dataset identities may be sensitive; share with
the appropriate audience. JSON and CSV remain available for dashboards.

`benchmark-get` retrieves the exact saved publication without reevaluation. The same HTML
format works on `benchmark-evaluate`, which does evaluate its supplied inputs. See the
[Slice 29 contract](../development/slice-29.md).

## Tune CodeQL resources

```bash
uv run traceproof scan-run RUN_ID /absolute/approved.ql --threads 1 --ram-mb 4096
```

The same options work on `codeql-extract`, `codeql-analyze` and `scan-import`.
Defaults remain 2 threads and 2048 MB. Allowed ranges are 1–64 threads and 2048–262144 MB;
choose values your machine can support. Pipeline commands apply them to both stages.
CodeQL treats these as tuning inputs, not hard process limits. Leave room for the OS,
Python and JVM overhead; OpenShift pod requests/limits will require separate configuration.

`codeql-status` and `scan-report` expose each new attempt's `requested_resources`.
Older attempts have no inferred resource record. Changing options does not force an
existing batch row to run again: `scan-import` still requires `--rescan` for existing
query attempts. See [Slice 28](../development/slice-28.md) for scope and validation.

## Export original SARIF for a viewer

```bash
uv run traceproof scan-history REPO_ID
uv run traceproof get-sarif REPO_ID ATTEMPT_ID > results.sarif
```

Choose the exact query attempt, also available in a published report's `attempt_id`.
The command verifies repository scope, the stored SHA-256 and the 16 MiB file limit
before writing original bytes. Completed and partial attempts with a recorded digest
are eligible; unavailable, linked or modified artifacts fail. Nothing is rescanned.
Errors go to stderr with exit 1; check exit status because shell redirection can leave
an empty file on failure. Use a new destination to avoid overwriting an existing export.

Raw SARIF may expose source-related messages, flows, paths and diagnostics. Review it
before sharing; use the summary CSV for routine dashboard consumption. The original
SARIF does not include later TraceProof model/operator decisions. Consult the matching
report for readiness: partial or zero-alert output does not establish a secure repository.
See [Slice 27](../development/slice-27.md) for the retrieval contract.

## Retrieve reports for an import batch

After `scan-import`, inspect report availability or export a dashboard input:

```bash
uv run traceproof import-reports IMPORT_ID --limit 100
uv run traceproof import-reports IMPORT_ID --offset 100 --limit 100
uv run traceproof import-reports IMPORT_ID --limit 1000 --format csv > import-reports.csv
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format html > report.html
```

Rows stay tied to the runs admitted in that import. Status distinguishes intake not ready,
not analyzed, report not published and published. A published report can describe failed
analysis; check analysis status and static readiness. Candidate counts are observations,
not verified vulnerabilities. Blank CSV counts mean unknown, not zero.

Only the newest report version matching the admitted run's latest attempt is selected.
There is no fallback to older reports or newer repository submissions. Publication captures
advisory/review state at that time; republish to include later reviews. JSON includes
page counts and `next_offset`; CSV contains only selected rows with stable ID columns.
Default page size is 100, maximum 1000. Separate pages may observe new work. This read-only
command makes no model calls and includes no source snippets. See the
[Slice 26 contract](../development/slice-26.md).

## Start here

TraceProof captures source, indexes Python, runs an approved local CodeQL query, and publishes reviewable candidates. Models can advise on those candidates; they cannot confirm vulnerabilities or suppress them. Operator assertions are recorded separately. A successful command, zero candidates, or `ready_for_review` does not establish that a repository is secure.

Install the locked development environment and initialize local storage:

```bash
uv sync --locked
uv run traceproof --help
uv run traceproof init
uv run traceproof get-report --help
```

Use `uv run traceproof` in the examples below. An activated project virtual environment also provides `traceproof`. Commands accept `--help`; the global `--state-dir` option goes **before** the command. Its default is `.traceproof` relative to the current directory. Keep using the same state directory throughout a workflow:

```bash
uv run traceproof --state-dir /absolute/local/state init
```

`init` creates or upgrades the database; it is not a reset command. Current migrations are applied explicitly, not on every read. Keep state on trusted local disk, not shared network storage. Source archives, raw tool outputs and evidence can be sensitive. The local OS account is the access boundary; repository ownership checks are not multi-user authentication.

## Understand the identifiers and outputs

Copy IDs from actual command responses; uppercase names below are placeholders.

| Identifier | Meaning / where to obtain it |
| --- | --- |
| `REPO_ID` | Your stable repository label in the CSV |
| `IMPORT_ID` | One CSV admission, returned by `import-csv` |
| `RUN_ID` | One admitted row's run, returned in import results |
| `SNAPSHOT_ID` | Captured source identity, returned by `run-status` after worker success |
| `EXTRACTION_ID` | CodeQL database extraction attempt, returned by `codeql-extract` |
| `ATTEMPT_ID` | Security query attempt, returned by `codeql-analyze` / `scan-report` |
| `CANDIDATE_FINGERPRINT` | Candidate identity within a scan, returned by `scan-report` |
| `BUNDLE_ID` | Bounded evidence package, returned by `build-bundle` |
| `REPORT_ID` | Immutable published summary version, returned by `publish-report` |

Commands normally print JSON. Request/storage errors produce a nonzero exit code, often with JSON on stderr. Durable failures can still exit zero: inspect row states, extraction/query `status`, bundle gaps, triage disposition and readiness. Scripts must inspect both the exit code and returned fields. `acceptance-run` and benchmark validation have additional explicit failure exit behavior.

To recover run or query-attempt IDs, including work without a published report:

```bash
uv run traceproof run-history REPO_ID --limit 100
uv run traceproof scan-history REPO_ID --limit 100
uv run traceproof scan-history REPO_ID --run-id RUN_ID --offset 0 --limit 100
```

Follow `next_offset` until null. Pages contain at most 1000 rows, sorted by newest run admission and then newest attempt within each run. New work can shift offset pages between requests; this is not a frozen export. Failed attempts remain visible, unknown counts are null, and a run with no query attempt has no scan-history rows. Extraction attempts are separate: use `extraction-history` to find IDs for `codeql-status`. Use `report-history` for published summary IDs.

## First walkthrough: capture and index synthetic source

The included generator creates a small benign archive. It does not execute the source.

```bash
uv run python examples/create_archive.py --output work/guide-input
uv run traceproof import-csv work/guide-input/repos.csv --input-root "$PWD/work/guide-input" --key guide-import-1
uv run traceproof worker IMPORT_ID --max-items 1
uv run traceproof import-status IMPORT_ID
uv run traceproof run-status RUN_ID
uv run traceproof verify-snapshot SNAPSHOT_ID
uv run traceproof index-run RUN_ID
uv run traceproof query-index RUN_ID --kind symbols
uv run traceproof repo-report synthetic-demo --run-id RUN_ID --format markdown
```

Expected checkpoints: the row is admitted, worker captures a snapshot, the run becomes `snapshotted`, and the Python index becomes ready. `repo-report` is **index coverage**, not the published vulnerability summary. Re-running indexing resumes checkpoints or reuses the same completed snapshot/parser index after source verification.

For your own inputs, CSV requires `repo_id,source_type,source_uri,owner,classification`; optional columns are `sha256,scan_profile`. Use `source_type=pvc`, an absolute archive path beneath `--input-root`, and `scan_profile=standard` if supplied. This source type works on laptop disk; no PVC is required locally. Supported archives are TAR, TAR.GZ and ZIP. Git URLs and GCS objects are not yet acquired.

Finish writing archives before admission. Supply `sha256` to pin original archive bytes before capture. Without it, capture time determines the pinned bytes. Reusing an import key with identical CSV bytes and root retrieves the same admission; changed source should use a new submission key. Invalid rows are reported independently. Links, path traversal and ambiguous archive members are rejected; nested archives are not recursively unpacked.

## Run CodeQL and inspect candidates

Before scanning, run `uv run traceproof doctor --query /absolute/approved.ql` for local
prerequisite diagnostics and suggested fixes. `blocked` exits 1; omitting the query can
return `incomplete` with exit 0. This command neither runs CodeQL nor changes the schema.
It checks availability, not query compilation, sufficient capacity or enterprise approval.
See [preflight details](../development/slice-22.md).

For an already captured run, the source-only stages can be executed together:

```bash
uv run traceproof scan-run RUN_ID /absolute/approved.ql --extraction-timeout 300 --query-timeout 600
```

This indexes, checks readiness, extracts, queries and publishes the exact attempt. It
never invokes an LLM. Inspect returned `status` and IDs: index/extraction failures stop
with no new report, while failed query attempts produce incomplete reports. Repeating
the command starts fresh extraction/queries; it is not an automatic retry. If publication
fails, find the attempt with `scan-history` and publish it explicitly. Individual stages
below remain useful for diagnosis. See [scan-run details](../development/slice-21.md).

To scan a captured CSV batch sequentially, use `scan-import IMPORT_ID QUERY --limit 5`.
Follow its `next_offset` with `--offset`; page positions include rejected/uncaptured rows.
The default limit is one row. Existing query attempts, including failures, are skipped
unless you pass `--rescan`. Inspect each row's outcome; mixed outcomes can exit zero.
Expected row errors do not block later rows, but infrastructure errors stop the command.
Per-run results are durable; save the JSON batch summary yourself. See
[batch scanning](../development/slice-25.md).

CodeQL must be on PATH, with an approved query and its dependencies installed locally. TraceProof does not download packs during analysis. Local acceptance has used CodeQL 2.27.0 and `codeql/python-queries` 1.8.10; the enterprise must supply its approved versions and usage entitlement.

```bash
uv run traceproof codeql-extract RUN_ID --timeout 300
uv run traceproof codeql-status EXTRACTION_ID
uv run traceproof codeql-analyze EXTRACTION_ID /absolute/CodeInjection.ql --timeout 600
uv run traceproof scan-report REPO_ID --run-id RUN_ID
```

Extraction uses Python build mode `none`. Inspect extraction success before analysis. Query failure, timeout and invalid SARIF are durable outcomes. The benign first walkthrough may have no candidates. For a reproducible vulnerable/fixed/incomplete demonstration, use a **new** output directory and an installed `CodeInjection.ql` entry:

```bash
uv run traceproof acceptance-run work/guide-acceptance /absolute/CodeInjection.ql --timeout 300
```

This creates isolated state under `work/guide-acceptance/state`, synthetic input archives, reports in five formats and `acceptance.json`. It checks that the seeded case has a candidate, its fixed counterpart does not, and an invalid Python fixture remains incomplete. It makes no model calls. The runner gates analysis on indexing; individual CLI stages remain separately callable, so operators must inspect gates themselves.

To inspect this state, add `--state-dir work/guide-acceptance/state` before every subsequent command. Repository IDs are `acceptance-vulnerable`, `acceptance-fixed` and `acceptance-incomplete`; run/report IDs are in the scorecard.

## Inspect evidence and request advisory triage

For a candidate returned by a scan:

```bash
uv run traceproof build-bundle ATTEMPT_ID CANDIDATE_FINGERPRINT
uv run traceproof bundle-status BUNDLE_ID
uv run traceproof evidence-policy py/code-injection
uv run traceproof triage-budget RUN_ID 100000
uv run traceproof triage BUNDLE_ID examples/triage-replay-config.json guide-triage-1 --replay examples/triage-replay-response.json
uv run traceproof triage-report RUN_ID
```

The supplied replay is offline, uses fictional rates/usage and abstains. `100000` micro-USD equals $0.10 in the ledger, not a replay charge. The run budget cannot be changed once set. Partial bundles, unsupported rules and exhausted budgets prevent provider invocation. Reusing the same triage key with identical inputs retrieves the recorded result; a different request needs a different key and may consume budget.

Each new budget also has a fixed request limit, default 100. Configure it at creation
with `triage-budget RUN_ID 0 --max-requests 20` for a zero-priced local run, for example.
All distinct recorded requests count, including skipped or failed ones. A repeated key
does not consume another slot. The ledger exposes `max_requests` and `remaining_requests`;
exhaustion blocks new keys without invoking a provider. Migration 0008 gives existing
budgets a 100-request limit and preserves their history. See
[request-limit details](../development/slice-24.md).

Evidence bundles have fixed source/envelope limits. Missing context stays explicit. Model proposals are `needs_review`, `likely_false_positive` or `abstain`. The evidence gate supports narrow code-injection and command-injection claims; acceptance is not independent proof of exploitation. No model proposal removes a raw candidate.

For targeted inspection, `source-evidence RUN_ID PATH LINE END_LINE` reads a verified snapshot range; `call-context RUN_ID PATH --module-root ROOT` provides conservative call candidates. `expand-bundle BUNDLE_ID REQUEST_JSON` accepts a JSON array of objects containing `path`, `line`, `end_line`, `reason`, creating an immutable child within existing caps. Expansion is bounded to four requested ranges per step and two steps. Inspect its result before separately triaging the child with a new key. `check-evidence BUNDLE_ID DECISION_JSON` validates claims locally without a model call.

### Live providers

For local POC inference, run an Ollama daemon with a locally installed completion model,
edit `examples/triage-ollama-config.json` to select it, then use:

```bash
uv run traceproof triage-budget RUN_ID 100000
uv run traceproof triage BUNDLE_ID examples/triage-ollama-config.json local-triage-1
```

No API key or `--replay` is needed. The endpoint is numeric loopback only, source/classification
opt-in remains mandatory, and zero configured rates represent local compute without an
estimated monetary cost. Ensure your daemon/model is local-only. A successful model reply
must still pass evidence checks and never automatically confirms a vulnerability.
See [Ollama setup and limits](../development/slice-23.md).

Only `triage` with a non-replay configuration invokes a provider. Cloud operation requires an explicitly allowed source classification, HTTPS endpoint/host, model ID, pricing and transmission opt-in. Keep cloud credentials in the designated environment variable, outside source archives and configuration files. OpenAI uses Responses; Anthropic uses Messages. Ollama uses the local policy above. No automatic provider fallback is available.

Configuration fields:

| Field | Operator responsibility |
| --- | --- |
| `provider`, `model` | `openai` or `anthropic`, plus the approved model identifier |
| `endpoint`, `allowed_endpoint_hosts` | Full approved HTTPS endpoint and exact hostname allowlist |
| `allowed_classifications` | Source classifications approved for this endpoint |
| `allow_source_transmission` | Must explicitly be `true` to send source |
| `api_key_env` | Name of environment variable containing the key; explicitly use `TRACEPROOF_ANTHROPIC_API_KEY` for Anthropic to avoid the OpenAI default |
| `ca_file` | Optional local CA file for TLS verification |
| `input_micro_usd_per_1k`, `output_micro_usd_per_1k` | Operator-supplied rates, in micro-USD per thousand tokens; no built-in prices |
| `max_output_tokens`, `timeout_seconds` | Output and request bounds; defaults 1024 tokens and 60 seconds |

Invoke `triage BUNDLE_ID CONFIG_JSON KEY` without `--replay`. The transport disables inherited proxies, redirects and retries. A bank gateway requiring proxy routing or another authentication method needs integration work; do not assume this local adapter covers it. Actual gateway/model compatibility and retention settings have not been validated by offline tests.

Unknown usage, interrupted requests and ambiguous provider failures retain reservations. A later triage operation marks interrupted running calls unknown; a read alone does not reconcile them. Do not clear ledger entries or automatically issue a new key to retry a possibly charged call. There is no operator refund/reconciliation command yet. Anthropic cache tokens are unexpected because caching is not requested; reported cache usage keeps accounting unknown. Configured reservations are not provider invoices or a guaranteed external spending limit.

## Publish, select and share a report

```bash
uv run traceproof publish-report REPO_ID
uv run traceproof report-history REPO_ID
uv run traceproof resolve-report REPO_ID --selection latest-attempt
uv run traceproof resolve-report REPO_ID --selection latest-completed
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format html > report.html
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format markdown > report.md
uv run traceproof get-report REPO_ID --report-id REPORT_ID > report.json
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format scan-csv > scan.csv
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format candidates-csv > candidates.csv
```

Publication reads stored state without invoking analysis. New triage/review state needs a new publication to appear in summaries; identical inputs reuse the same report. Exact report IDs stay immutable. Use `publish-report --run-id RUN_ID --attempt-id ATTEMPT_ID` for historical work.

`latest-attempt` never falls back to older work. `latest-completed` selects published Python static review-ready work, and its JSON envelope discloses the current run/attempt plus a warning if the chosen report is older. It does not claim security completion. No eligible report returns a null report with a warning. Preserve the envelope when sharing a historical selection; exporting only its embedded report loses the current-work disclosure. Selection is currently limited to 10,000 report versions per repository.

| Command | Question answered |
| --- | --- |
| `run-status` | Was source captured? |
| `run-history` / `scan-history` | Which runs and query attempts exist, including unpublished work? |
| `repo-report` | What Python syntax was indexed, and where are the gaps? |
| `scan-report` | What did this static-analysis attempt observe? |
| `triage-report` | What advice and costs were recorded for the run? |
| `resolve-report` | Which published report fits my selection, and is it current? |
| `get-report --report-id` | What did this exact immutable summary say? |

For dashboards, join scan and candidate CSVs on `report_id`. Scan CSV has report-level counts; candidate CSV has candidate rows. Preserve scan rows when there are zero candidates. Unknown counts remain unknown, not zero. Summary formats omit raw source, model prose and review notes, but metadata and paths can remain sensitive. Raw scan/evidence/history commands expose more detail.

`compare-reports REPO_ID BASELINE_REPORT_ID CURRENT_REPORT_ID --format markdown` compares exact versions without scanning. One-sided observations are not automatically fixed/new vulnerabilities; scope changes and ambiguous matches stay explicit.

## Record an operator review

First inspect `review-history REPO_ID ATTEMPT_ID CANDIDATE_FINGERPRINT` and the evidence bundle. Save a request such as the following, replacing the bundle placeholder and using the current history revision (zero initially):

```json
{
  "reviewer_label": "local-operator",
  "state": "needs_review",
  "rationale": "Confirm the input trust boundary with the application owner.",
  "bundle_id": "REPLACE_WITH_ACTUAL_BUNDLE_ID",
  "evidence_ids": [],
  "expected_revision": 0
}
```

```bash
uv run traceproof record-review REPO_ID ATTEMPT_ID CANDIDATE_FINGERPRINT review.json guide-review-1
uv run traceproof publish-report REPO_ID
```

Allowed states are `confirmed`, `false_positive`, `needs_review`, `deferred`. Definitive assertions require a ready bundle and valid evidence citations. Review keys are idempotent; a stale revision requires reading history before intentionally making another assertion. History is append-only, reviewer identity is self-declared, and these assertions do not set independent verification or measured precision.

## Benchmark evaluation

Keep labels outside analyzed archives. `benchmark-schema` prints manifest, labels and evaluation-plan schemas. `benchmark-check MANIFEST --labels LABELS` checks the contract; add `--check-local-snapshots` for stored identity alignment. Example files in `examples/` have synthetic placeholder digests and are not a real corpus.

`benchmark-evaluate MANIFEST LABELS PLAN --format markdown` evaluates exact published report IDs against evaluator-only labels without running scans. The plan pins analysis configuration and report selection. Results are provisional candidate-location recall proxies, not confirmed recall or precision. The 50-repository bank benchmark has not been run. See [evaluation details](../development/slice-11.md).

For dashboard ingestion, use `--format summary-csv`, `repositories-csv`, `labels-csv` or
`candidates-csv` and redirect each output to a separate file. Keep canonical JSON too.
Each populated CSV row carries the scorecard ID and input digests; verify they match
before joining on scorecard/repository IDs. Never sum the one-row summary after joining
detail tables. Null metrics are blank, zero remains zero, and lists/count maps are JSON
cells. Empty detail tables have headers only, so retain the summary. These exports expose
evaluator labels and matching metadata; share only with the authorized evaluation audience.
See [benchmark CSV contracts](../development/slice-17.md).

Evaluator version 2 also reports results by CWE in JSON and Markdown. Use
`--format weaknesses-csv` to export those rows. Class denominators retain missing,
ambiguous and unsupported labels. `no_labels` means no measurable recall value;
`incomplete` means unresolved evaluation gaps; `evaluated` may still include misses.
Do not average class percentages: sum numerators and denominators for the overall proxy.
Join using scorecard ID and CWE. Reevaluation creates new scorecard IDs; legacy results
are unchanged. See [per-class metrics](../development/slice-18.md).

To save an evaluation for later retrieval, run `init` for migration 0007, then:

```bash
uv run traceproof benchmark-publish MANIFEST LABELS PLAN
uv run traceproof benchmark-history DATASET_ID --limit 100
uv run traceproof benchmark-get DATASET_ID SCORECARD_ID --format markdown
uv run traceproof benchmark-get DATASET_ID SCORECARD_ID --format weaknesses-csv
```

Publication reuses identical scorecards and stores changed evaluations as separate IDs.
Retrieval supports JSON, Markdown and all five benchmark CSV formats without reevaluation
or input files. History includes incomplete publications. Protect evaluator-sensitive
records and retain approved inputs separately for reproducibility. See
[durable scorecards](../development/slice-19.md).

Use `benchmark-compare DATASET_ID BASELINE_SCORECARD_ID CURRENT_SCORECARD_ID --format
markdown` to compare saved evaluations. Incompatible datasets, labels, evaluators, rule
sets or incomplete results produce explicit reasons and unknown deltas. Comparable
results show provisional location matches gained/lost and current-minus-baseline proxy
deltas. Query/tool changes are disclosed, not assigned causal credit. No scans or input
files are needed. See [benchmark comparison](../development/slice-20.md).

## Recovery and routine operations

| Symptom | Action |
| --- | --- |
| Database uninitialized / older schema | Verify `--state-dir`, quiesce writers and run `init`; preserve a consistent backup before upgrades |
| Another local worker holds the lock | Let it finish; do not remove the lock to force concurrent work. Process death releases the OS lock |
| Interrupted intake | Re-run `worker IMPORT_ID`; recovery is capped at three attempts. Correct rejected/failed inputs and submit under a new key |
| Interrupted indexing | Re-run `index-run RUN_ID`; verified checkpoints are reused |
| CodeQL failure or timeout | Inspect `codeql-status` / `scan-report`, local diagnostics, tool and query availability before explicitly starting a new attempt |
| No current report | Publish the latest stored attempt, or intentionally select an exact ID / latest-completed envelope |
| Integrity failure | Preserve state for investigation; restore a verified backup or capture a new authorized run, rather than altering digests |
| Unknown/exhausted triage budget | Inspect `triage-report`; no automatic refund or budget increase exists |
| Disk filling | Stop new work and inspect storage. Automatic artifact cleanup is not implemented; do not delete referenced artifacts |

For a local backup, stop all TraceProof writers, copy the whole state directory (including SQLite sidecar files and artifacts), and keep tool/query/configuration provenance separately. Do not copy only the database during active writes. Restore to another local directory, run `init` as appropriate, verify snapshots and retrieve exact reports before relying on it. This is local operational guidance, not a production backup/restore qualification.

No explicit pause/cancel controls exist yet. `worker --max-items` bounds intake work; rerunning resumes supported checkpoints. There is no background all-stage scheduler: running `worker` captures archives, not the entire security pipeline. Do not infer 1,000-repository/day capacity from this POC.

## Further reference

Use `COMMAND --help` for exact arguments and pagination flags. [Slice contracts](../README.md) document version-specific limits; the [implementation plan](../plans/implementation-plan.md) tracks upcoming capabilities. The API companion guide is scheduled with the first hosted API and will add HTTP authentication, submission/polling, retry and error workflows to its OpenAPI reference.

## Initial Java static profile (Slice 37)

`codeql-extract`, `scan-run` and `scan-import` accept `--language java`; Python remains
the default. Supply an installed Java CodeQL query to analysis or the scan runner.
Each invocation selects one language; there is no automatic multi-language fan-out.
Reports retain that language and an inventory of other detected source languages.

This first Java profile supports dependency-free source using build mode `none`. It
rejects Maven/Gradle/Ant build descriptors, wrappers, JARs and Kotlin inputs. Spring,
external dependencies and generated code are not qualified. Java semantic indexing
and LLM evidence support are still pending, so Java reports remain **incomplete**,
even when CodeQL succeeds. Retrieve them using the exact report ID or latest-attempt;
`latest-completed` requires static review readiness and will not select them.

The repeatable local acceptance script uses a new output directory:

```sh
uv run python scripts/validate_java.py /path/to/java-queries/Security/CWE/CWE-089/SqlConcatenated.ql work/java-acceptance
```

It checks a JDBC concatenation fixture (one candidate) and a prepared-statement
fixture (zero), preserves incomplete readiness, and makes no model calls. These
fixtures do not establish repository security or measured recall.

### Java syntax coverage (Slice 38)

After `uv sync`, Java scan-run/scan-import automatically build a bounded syntax index.
A blocked syntax gate stops the runner before extraction and returns per-file statuses.
Standalone codeql-extract records syntax coverage but can still attempt extraction;
inspect the retained scope. Successful reports expose the index in language_scope.
No new migration or command is required. Syntax parsing does not establish Java
semantic or Spring support; readiness remains incomplete. See Slice 38 for limits.

### Spring annotation observations (Slice 39)

New Java indexes include `framework_observations` in the retained syntax index.
Each observation identifies its file/hash, annotation line and declaration target.
The first 200 matching annotation names are returned; inspect total/truncated.
A Spring namespace hint is not proof of runtime binding or an externally reachable
endpoint. Wildcard imports remain unresolved. No Java LLM policy or build-profile
support is enabled by these observations. Reusing an old report returns its original
contents; a new scan uses the versioned parser and retains fresh observations.

### Source-only Spring acceptance (Slice 40)

Run `uv run python scripts/validate_spring.py QUERY_PATH NEW_OUTPUT_DIRECTORY` with
an installed Java `SqlTainted.ql`. The suite checks vulnerable/fixed/foreign-annotation
controllers and malformed source. Outputs include validation.json, exact JSON/HTML
reports and a source-containing vulnerable evidence bundle. No model calls or Spring
builds run. A retained modeled path is not proof of deployed reachability. Java
readiness remains incomplete; Maven/Gradle and Java LLM policies are still pending.

### Java SQL advisory gate (Slice 41)

Gate 4 enables only java/sql-injection with complete small-file Java context,
explicit Spring RequestParam and executeQuery syntax on retained flow endpoints.
It supports needs_review with unknown guards; Java false-positive suggestions cannot
pass yet. Build a new bundle to retain full Java files of at most 40 lines within
existing byte limits. Larger/partial context stays insufficient. Old bundles and
reports remain unchanged; old triage keys may conflict across gate versions.
Use check-evidence for a local recheck without model spend. Existing provider,
classification and budget requirements apply to new triage. Java reports remain
incomplete; passing evidence is advisory and never confirms or suppresses a finding.

### Java context expansion (Slice 42)

Gate 5 can combine same-snapshot/file/hash excerpts into complete Java context.
Use the existing expand-bundle workflow to supply missing ranges, then check-evidence
against the new bundle. Missing lines or conflicting overlaps fail conservatively.
All expansion byte, range, depth and snippet limits still apply; no automatic model
calls occur. This supports larger files within those limits, but does not supply missing
flow steps or enable Java negative advice. Gate-version changes may conflict with old
triage keys; preserve uncertain calls rather than retrying them under new identities.

### Maven/Gradle layouts without builds (Slice 43)

Use `--language java --java-profile source-only` on codeql-extract, scan-run or
scan-import. CodeQL receives a verified Java-only copy: descriptors, wrappers, JARs,
Kotlin and other files are omitted. Inspect omitted-file counts and unresolved dependency/
generated-code coverage in language_scope. This is not a qualified Maven/Gradle build
or an OS/network sandbox. Default dependency-free behavior is unchanged. Batch skips
are profile-specific, so switching profiles may perform a fresh scan. No migration.

### Automatic language selection (Slice 44)

`--language auto` works on extraction, scan-run and scan-import. Exactly one detected
source language must be present and supported (Python/Java); mixed and unsupported
inventories require an explicit choice. Python remains the default when omitted.
Supply the correct query yourself; auto does not choose queries or run all languages.
For Java build layouts, add `--java-profile source-only` explicitly. Reports retain
whether language selection was automatic. scan-import applies one query across its
page, so group repositories by query applicability. No migration or build execution.

### Initial C# scanning (Slice 45)

Select --language csharp (or auto for a C#-only snapshot) and provide a compatible
C# query plus --allow-csharp-downloads. CodeQL may download an SDK and access NuGet;
without the opt-in, extraction is blocked. Only .cs files enter the copied source tree.
Project files, binaries and Razor views are omitted. Reports remain incomplete,
and C# LLM triage is unsupported. Classic ASP.NET misses the fixture without matching references; Slice 46 below
resolves it for the pinned net48 profile. Broader ASP.NET coverage remains unqualified. See Slice 45 for reproduction and bank prerequisites.

### Pinned C# dependencies (Slice 46)

Use --csharp-dependency-profile PATH with C# extraction/scan commands. SDK and reference
files are verified against the manifest; see Slice 46 for pin_csharp_dependencies.py.
The local working example is work/slice46-dependencies/profile.json. The matching net48
profile resolves the known classic fixture miss. Select profiles matching the target
framework; this does not qualify arbitrary projects. SDK/CodeQL version mismatches fail.
Profile changes prevent reuse of an earlier profile's scan attempt.

For macOS offline extraction, add --csharp-offline and omit --allow-csharp-downloads.
This requires the pinned profile. The app checks and applies network denial to SDK/
CodeQL version inspection and extraction, including child processes. Failure to establish
isolation blocks extraction; there is no network fallback. Successful extraction records
network_denial_verified=true. This option does not isolate query execution or LLM calls,
and is not a filesystem/build sandbox. Linux is unsupported by this option and fails
closed. The earlier explicit download opt-in remains available for other local runs.
See Slice 47 for validation and reproduction.
Mount SDK/reference directories read-only in deployment and give each scan writable
scratch. The macOS SDK is not portable to a Linux/OpenShift worker. Reports remain
incomplete and C# LLM advice is still unsupported. No migration.

### Pinned Java JAR profiles (Slice 50)

Use --java-dependency-profile PATH on codeql-extract, scan-run or scan-import with
Java (or auto selecting Java). scripts/pin_java_dependencies.py creates a versioned
manifest of approved local Maven-layout JARs; see the container operator guide. The
profile is validated before extraction and rechecked afterward. It participates in
scan reuse and report comparison. CodeQL version 2.27.0 is the qualified interface.

Supplying a profile does not enforce offline execution. CodeQL can infer additional
artifacts; keep network disabled in the runner when scanning offline. The container
Spring fixture uses a six-JAR pinned profile; this is not broad Spring qualification.
No Maven/Gradle builds or live LLM calls are introduced. No migration.

### C# SQL advisory evidence (Slice 56)

Gate 6 enables advisory review for `cs/sql-injection` when complete bounded C# source
contains an explicit ASP.NET Core FromQuery parameter and a CommandText assignment
anchored to the endpoints of a complete retained CodeQL thread. It supports the
qualified Core MVC/minimal API fixture shapes. Classic FromUri, implicit MVC binding,
raw request access, alternate SQL APIs and guard counterevidence remain unqualified.

Use the existing bundle-build, check-evidence and triage workflows. New bundles use
builder 5 and retain complete C# files up to 40 lines within existing byte budgets.
Larger files require consistent evidence expansions covering every line; reconstructed
context is capped at 16 KiB. Missing context, parser failure, conditional compilation,
ambiguous imports/aliases and local FromQuery lookalikes fail closed. A passing gate
checks quoted syntax and recorded flow consistency; it proves neither runtime request
binding nor exploitability. C# false-positive advice cannot pass this gate.

Provider classification, consent, token budgets and model configuration still apply.
No provider is enabled automatically. Old bundles/reports remain immutable; build a
new bundle to use the new context policy. Existing triage keys may conflict across
gate versions; use a new request key. Reports remain incomplete and findings remain
unreviewed until the existing operator-review workflow is used. This supersedes earlier
blanket statements that all C# triage is unsupported; support is narrow and advisory.
