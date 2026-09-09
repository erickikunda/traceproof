# Slice 12 — Append-only operator review

Slice 11 is committed as `d65f4e2`. This slice begins M3.8's human-review workflow and
extends M2.7's decision history. It does not complete finding-family identity, enterprise
reviewer authentication, suppression expiry or rule-gap tracking.

## Local operator workflow

Apply migration 0006 with `traceproof init`. Inspect the candidate's evidence and current
review revision, then prepare a request:

```json
{
  "reviewer_label": "local-reviewer",
  "state": "needs_review",
  "rationale": "Further inspection of the validation path is required.",
  "bundle_id": "<exact evidence-bundle SHA-256>",
  "evidence_ids": ["E1"],
  "expected_revision": 0
}
```

Replace the placeholder digest with a real bundle ID. `expected_revision=0` means no prior
review. Subsequent requests must name the revision returned by `review-history`.

```bash
uv run traceproof review-history REPO_ID ATTEMPT_ID FINGERPRINT
uv run traceproof record-review REPO_ID ATTEMPT_ID FINGERPRINT /absolute/review.json review-1
uv run traceproof publish-report REPO_ID --run-id RUN_ID --attempt-id ATTEMPT_ID
```

States are `confirmed`, `false_positive`, `needs_review` and `deferred`. Any new valid
state may follow an earlier one, with fresh rationale and expected revision. Returning
to `needs_review` preserves the earlier decision as history. There is no `fixed` state
and no automatic carry-forward to another candidate, attempt or snapshot.

The request is strict JSON capped at 16 KiB, with duplicate keys rejected. Reviewer and
rationale must be nonblank, unknown fields/states are rejected, and cited IDs must be
unique and present in the named bundle. Confirmation/false-positive assertions require
at least one citation and a ready bundle. Deferred/needs-review entries may use partial
bundles and empty citations. Bundle ownership and content integrity are checked. These
are reference/completeness checks, not proof that a review rationale is correct.

## Consistency, identity and audit boundary

Migration 0006 adds `operator_reviews`, keyed by content SHA-256 with unique candidate/
revision and candidate/request-key pairs. A transaction under the existing local worker
lock verifies ownership and the expected revision, then appends the next revision.
Concurrent/stale reviewers cannot silently overwrite each other. An identical key and
request returns its original entry even after newer reviews exist; conflicting reuse
fails. `review-history` returns current revision separately from its paginated rows.

Requests are bound to an exact repository, analysis attempt, candidate and evidence
bundle. Content hashes detect changed review contents during history retrieval and
report publication. The raw candidate, model ledger and previous reports are never
rewritten. This is application-level append-only behavior under the local storage trust
boundary, not tamper-proof storage against the OS/database owner or a distributed lease.

`reviewer_label` is supplied by the caller. Every entry records
`reviewer_authenticated=false` and `independently_verified=false`. The POC cannot prove
a human authored the request or verify the claimed identity. Models have no review tool
or automatic path into this ledger. Enterprise identity/authorization and audit controls
remain required before treating these records as authoritative organizational decisions.

## Report behavior

Report projection version 4 adds per-candidate operator state/history and current-state
counts. HTML/Markdown display a distinct operator-review column; candidate CSV includes
the state. Summaries include event IDs, revisions, times and evidence references, but
omit reviewer labels and free-text rationale. The explicit history command exposes the
full local notes, which may contain sensitive information.

Raw `adjudication=unreviewed` remains distinct from the operator assertion. All candidates,
including those asserted false positive, remain in reports; candidate counts do not
decrease. Verified finding count remains null, coverage remains unverified, and static
readiness gaps remain visible. Explicit republication captures new reviews in a new
immutable report version. Historical report IDs retain their original view.

Comparison version 3 includes operator-review state alongside model advice. Benchmark
evaluation remains based on raw candidate observations; it does not turn unauthenticated
operator assertions into precision, confirmed recall or ground-truth labels.

## Validation and remaining work

252 tests passed, including idempotent retries after later revisions, stale/conflicting
writes, ownership/evidence failures, partial-bundle constraints, tamper detection, raw
candidate preservation, private-note exclusion, immutable report versions, duplicate
JSON keys, invalid request objects and CLI behavior. The inherited duplicate ZIP fixture
emits one expected warning.

An isolated SQLite backup of the synthetic smoke state was upgraded to 0006. A synthetic
`needs_review` entry exercised append/retry/history and report-version behavior while
preserving the original database and old report. No real vulnerability confirmation,
source execution or paid model call was performed by this smoke test.

Useful POC work remains: reviewed family/occurrence identity across edits, authorized
review workflows, suppression lifecycle, stronger benchmark matching and richer exported
scorecards. No external blocker prevents further local development.
