# TraceProof CLI user and operator guide

**Scope:** laptop POC through Slice 18, SQLite schema 0006. Commands are run from the repository checkout on Linux/macOS using Python 3.12+. This guide describes implemented behavior. Git/GCS acquisition, HTTP API hosting, distributed workers, authenticated reviewers and OpenShift deployment are future work.

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

Follow `next_offset` until null. Pages contain at most 1000 rows, sorted by newest run admission and then newest attempt within each run. New work can shift offset pages between requests; this is not a frozen export. Failed attempts remain visible, unknown counts are null, and a run with no query attempt has no scan-history rows. Extraction attempts are separate: retain their IDs for `codeql-status`. Use `report-history` for published summary IDs.

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

Evidence bundles have fixed source/envelope limits. Missing context stays explicit. Model proposals are `needs_review`, `likely_false_positive` or `abstain`. The evidence gate supports narrow code-injection and command-injection claims; acceptance is not independent proof of exploitation. No model proposal removes a raw candidate.

For targeted inspection, `source-evidence RUN_ID PATH LINE END_LINE` reads a verified snapshot range; `call-context RUN_ID PATH --module-root ROOT` provides conservative call candidates. `expand-bundle BUNDLE_ID REQUEST_JSON` accepts a JSON array of objects containing `path`, `line`, `end_line`, `reason`, creating an immutable child within existing caps. Expansion is bounded to four requested ranges per step and two steps. Inspect its result before separately triaging the child with a new key. `check-evidence BUNDLE_ID DECISION_JSON` validates claims locally without a model call.

### Live providers

Only `triage` with a live configuration invokes a provider. Start with replay. Live operation requires an explicitly allowed source classification, HTTPS endpoint/host, model ID, pricing and transmission opt-in. Keep credentials in the designated environment variable, outside source archives and configuration files. OpenAI uses Responses; Anthropic uses Messages. No automatic provider fallback is available.

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
