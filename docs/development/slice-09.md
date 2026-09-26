# Slice 09 — Reproducible acceptance and static-review readiness

Slice 08 is committed as `50b33e9`. This slice delivers the local Python fixture
demonstration in M0.6 and strengthens M2.3 with an explicit, limited readiness projection.
It does not establish complete coverage, vulnerability adjudication or model accuracy.

## Real acceptance workflow

```bash
uv run veriflow acceptance-run work/acceptance-001 /absolute/CodeInjection.ql --timeout 300
```

The output directory must not exist. The command creates isolated state and three
synthetic archives using ordinary intake operations, indexes each snapshot, and runs
CodeQL extraction/query analysis only for ready Python indexes. Extraction uses normal
baseline counting. The caller supplies an approved local query entry; the runner does
not download packs, install dependencies or execute source/build scripts. Stage timeouts
apply separately to extraction and analysis; they are not a whole-suite deadline.

Expected assertions remain in the runner, outside the source archives. These fixtures
are workflow tests, not the bank's 50-repository benchmark and not a held-out quality
dataset. No model adapter or budget is configured, and reports must show zero model calls.

| Fixture | Source difference | Required result |
| --- | --- | --- |
| Vulnerable | Flask request value passed to `eval` on app.py line 5 | Completed query with exactly one `py/code-injection` candidate at the seeded location |
| Fixed | Return the request value without evaluating it | Completed query with zero candidates for this query; no clean verdict |
| Incomplete | Add a malformed Python file alongside the vulnerable app | Blocked Python index, extraction not requested, static analysis not started, candidate count unknown |

Each case publishes and retrieves an exact immutable report. JSON, HTML, Markdown,
scan CSV and candidate CSV files are written beneath the output directory. The runner
checkpoints `acceptance.json` after each completed case, including assertion booleans,
snapshot/run/report IDs, extraction status, CLI version, entry-query SHA-256 and elapsed
time. Query digests for analyzed cases must match the initially recorded entry digest.
The aggregate pass flag is true only after all cases pass. Failed assertions exit nonzero;
startup/storage failures also return CLI errors. Interrupted runs retain their local
artifacts but do not automatically resume; start a new output directory.

This command is intentionally an acceptance harness, not a general scan scheduler.
Its index gate controls its own dispatch. Existing explicit operator extraction/query
commands remain callable independently, with their stored diagnostics preserved.

## Published readiness

Report projection version 2 adds `static_review_readiness`, selected from the current
parser version's published index for the same snapshot and the selected scan attempt.
`ready_for_review` requires:

- A published Python index whose parsing/function-inventory gate is ready.
- A completed static-analysis attempt with execution complete.
- Zero recorded diagnostic errors and zero unmapped candidates.
- A known candidate count.

Missing/old-version/blocked indexes, failed analysis and unknown diagnostics produce
`incomplete` with explicit reasons. The report includes index identity/version and file
counts. The gate does not establish non-Python coverage, extraction soundness, complete
query applicability, runtime reachability or guard effectiveness. Existing
`coverage_verified=false`, `verified_finding_count=null` and `not_adjudicated` remain.

Readiness is visible in HTML/Markdown and CSV as well as JSON. Later index publication
creates a different report input digest and a new version when explicitly republished.
Historical reports remain immutable and show unknown readiness when the field is absent.
Comparison version 2 disables tentative anchor matching when either report has missing
or incomplete readiness; exact snapshot observations remain identifiable with scope gaps.
No database migration beyond 0005 is required.

## Validation evidence

The real suite completed with CodeQL 2.27.0 and the bundled Python query pack 1.8.10.
All three cases passed in approximately 15 seconds on this laptop. Both analyzed cases
extracted successfully with baseline counting enabled. The incomplete case did not
request extraction. All exact report retrieval checks passed, with no paid/model calls.
This small duration is not a throughput estimate for enterprise repositories.

All 212 automated tests passed (one expected warning from the duplicate ZIP fixture).
The automated suite covers missing/blocked/old-parser indexes, failed or unmapped static
results, immutable report updates, CSV readiness, legacy rendering, seeded-location
assertions, nonzero acceptance failure exits and readiness-aware comparison. A full
requirement register remains future work; these are the slice-specific mappings:

| Plan item | Evidence |
| --- | --- |
| M0.6 local fixture demonstration | Real `acceptance-run` scorecard and exported case reports |
| M2.3 incomplete work stays visible | `tests/test_acceptance.py` readiness and negative assertions |
| M2.8 report version/read compatibility | Immutable readiness update and historical-render tests |
| M3.7 conservative comparison | `tests/test_comparison.py` missing/incomplete readiness cases |

Remaining work includes broader vulnerability classes, finding-family/review state,
benchmark contracts/evaluation, live model gateway validation and production orchestration.
These acceptance fixtures should stay separate from benchmark labels and future tuning data.
