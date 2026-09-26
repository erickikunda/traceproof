# Slice 30: bounded candidate triage orchestration

```bash
uv run veriflow triage-attempt REPO_ID ATTEMPT_ID CONFIG_JSON BATCH_KEY --limit 5
```

Requires an existing per-run `triage-budget`. Selects candidates from an exact completed
or partial query attempt in fingerprint order, default one, maximum 100 per invocation.
`--offset` selects a page. Repository ownership is checked before bundle/model work.
Each selected candidate uses the existing base bundle builder and single-call triage
operation, including integrity, classification, opt-in, monetary/request limits and
evidence gates. No evidence expansion, automatic provider fallback or report publication
is added. Live configurations can transmit source and incur charges; replay uses
`--replay RESPONSE_JSON`. One replay response is reused across the selected page and
is only a transport fixture, not candidate-specific quality evidence.

Derived request keys hash the caller's batch key, exact attempt ID and fingerprint.
Repeating the same page/key/configuration reuses durable outcomes, including unknown
outcomes, without automatically retrying a provider. Changing policy with the same key
is a conflict. Use a deliberately new key only when another billed/limited request is
intended. Existing single-bundle calls under unrelated keys are not deduplicated against
batch calls. Prompt, bundle or gate changes can also cause a key conflict.

The batch continues after completed/evidence-rejected advice or unsupported/incomplete
evidence skips. It halts after any other returned triage state or an expected application
error. The JSON contains selected count, processed outcomes, status and `next_offset`.
A recorded outcome advances the offset even when it halts; an application error leaves
the offset on that candidate. Inspect the result and ledger before selecting another
page. `page_complete` means only that the selected page was visited, not that all candidates
or security obligations were completed. Mixed/halting outcomes can exit zero: inspect
`status`. Infrastructure errors stop the command and durable per-call records survive.

Each bundle/call retains its existing local lock; no lock spans the whole page. The batch
summary is not persisted, but request keys and triage IDs support ledger inspection.
No new concurrency or global deadline is introduced. Models cannot confirm or suppress
vulnerabilities. Publish a new report explicitly to include the new advisory history.
No database migration is required beyond 0008.

Tests cover real local bundle/ledger idempotency with a fake adapter, changed-policy
conflicts, monetary/request exhaustion, ownership, pagination, CLI policy wiring and
stopping before the next candidate after uncertain output. No live inference is used.
