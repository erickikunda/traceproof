# Slice 98 — Main Joern scan workflow with explicit advisory

## Outcome

scan-run and scan-import can now run a bounded Spring advisory page after a fresh Joern
Java scan. The operator explicitly supplies model configuration, review policy, request
key and candidate-page bounds; each run requires a preconfigured triage budget. Default
execution remains discovery-only. No database migration is required.

The pipeline publishes discovery first, runs the advisory page through the existing
budgeted batch-triage service, and publishes an updated report for the same exact attempt.
Advisory errors/stops are exposed without turning the report into a complete or clean
security verdict. Failed analysis skips advisory while retaining its report. Unsupported
engine/language/profile combinations and missing budgets reject before new extraction.

## Boundaries and continuation

An immutable AdvisoryOptions object groups model/adapter, policy, key and candidate-page
bounds. The default is one candidate, maximum 100. Repository row bounds remain separate.
The adapter wrapper counts actual invocations without changing adapter identity. Cached
ledger returns and preflight/budget blocks count zero. model_calls includes replay;
live_model_calls excludes it. Import totals aggregate row counts.

Existing-attempt skips skip the whole scan/advisory workflow, including attempts that have
no prior advice. Continue an existing attempt with triage-attempt and the same key/policy,
using the returned advisory.next_offset, then publish a fresh report. Rescanning creates a
new attempt and may incur new costs under the same immutable run budget. Import dispatch
pause/cancel is checked between repository rows, not inside a started advisory page.

Shared preflight, returned-claim validation, idempotency, reservations and provider controls
are reused. Only the default Java/Spring Joern profile supports the pipeline option today.
The HTTP API launch schemas are unchanged; CLI/Python expose this opt-in. Live model quality,
other language advisory policies, bank benchmark and OCP acceptance remain open.

## Validation

678 automated tests pass, with one existing duplicate-ZIP fixture warning. Ruff and diff
whitespace checks pass. Focused controls cover exact-attempt publication, invocation counts,
repeat skips, missing budgets, exhausted money/request limits, empty advisory pages, failed
scans, wrong engines/languages, bounded options and a CLI replay scan through the full path.

Seven restricted Linux cases passed in 52.590 seconds. Vulnerable and renamed cross-file
cases each produced one replay needs_review advisory; five negative cases produced none.
Fixed input was also explicitly rescanned: eight native scans, two replay invocations,
zero live calls. Repeated imports skip both stages and do not add ledger entries. Each
positive ledger accounts for 140 simulated micro-USD, not an external charge.

ARM64 image:
sha256:8614004c329da4c1963a548213c80fb5a37e5ea10f2fa378b7010e1768b8d5e6.
Artifacts: work/slice98-workflow-advisory-linux-final, including validation.json,
*-advisory.json and shareable HTML. Runtime uses arbitrary UID, read-only root, no network,
dropped capabilities and bounded resources. Default-skip help wording was restored after
the image run and checked locally; the explicit-advisory behavior is unchanged.

The initial acceptance check republished the fixed case after its additional rescan and
incorrectly expected the earlier report ID. The corrected check retrieves the immutable
ID returned by the original pipeline. Initial diagnostics remain in
work/slice98-workflow-advisory-linux. Report publication semantics were not changed.

## Next logical work

Extend the same explicit evidence/advisory contract to the bounded Python Flask profile,
starting with native/source-context eligibility. Preserve strict unknowns and refrain from
promoting synthetic intermediate nodes or other language profiles without their own minimum
acceptance. Reuse the now-complete workflow rather than further refining CLI mechanics.
Broader deployment API coverage, bank quality/throughput evidence and target OCP acceptance
remain separate gates.
