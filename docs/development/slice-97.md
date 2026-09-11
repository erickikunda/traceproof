# Slice 97 — Opt-in budgeted Joern Spring advisory

## Outcome

The existing triage and triage-attempt operations now accept an explicit
joern-spring-review-v1 policy. They reuse the durable ledger, per-run budgets, request
limits and adapter controls. The default registry and main Joern scan-run/scan-import path
remain discovery-only; model invocation requires a separate explicit advisory operation.
No database migration or external service is required for replay validation.

Before invocation, the selected policy requires native audit identity, source hashes,
complete context, ordered recorded path and supported Spring/SQL endpoint syntax. This
preflight determines eligibility only; it creates no advisory decision. Missing evidence
records incomplete_evidence with zero reservation/charge and no provider call. After
invocation, actual returned claims pass through the same explicit evidence gate. Negative
suggestions and fabricated claims abstain; no outcome verifies or suppresses a vulnerability.

## Identity, cost and reporting

The provider payload includes explicit engine/policy requirements and the packaged query
digest. Request identity also includes preflight results. Reusing a single-item key with
a changed policy/request/preflight conflicts; batch keys distinguish explicit/default
policies. Default request construction and batch keys are retained for existing callers.
Retries return the ledger entry without re-invocation. Uncertain transport failures retain
the full reservation, and cost/request caps still apply. Blocked ledger rows consume a
request slot, preserving the existing bounded-request behavior.

OpenAI, Anthropic and local Ollama prompt construction supports the policy under existing
classification, endpoint, pricing, API-key and source-transmission controls. Prompt shapes
are tested offline; live model quality and provider behavior are not validated here.
Replay rates exercise accounting and are not external charges.

Report projection 12 adds review_policy and engine_id to explicit-policy advisory history.
JSON and shareable HTML retain simulated status and incomplete security coverage. Existing
published reports remain immutable; publish a new report to include new advisory history.
The HTTP API launch schemas are unchanged; this opt-in is exposed through CLI/Python triage.

## Validation

667 automated tests pass; one existing duplicate-ZIP fixture warning. Ruff and diff
whitespace checks pass. New controls cover explicit/default selection, preflight syntax,
missing native evidence, budget exhaustion, timeout accounting, negative/fabricated claims,
idempotency and policy conflicts, changed-preflight cache conflicts, batch separation,
CLI replay invocation, report history and all three provider prompt shapes without network.

Seven fresh restricted Linux scan cases pass in 56.710 seconds. Vulnerable and renamed
cross-file candidates each receive one replay needs_review response. Repeating each request
preserves a single ledger entry and 140 simulated micro-USD accounted per candidate.
Five negative scan controls remain empty; the fixed fixture is also explicitly rescanned.
Total: eight native scans, two replay invocations, zero live model calls.

ARM64 image:
sha256:1e529686a14bd5e15fdc3704750b00241713621d358fde5852426063dd33b5c3.
Artifacts: work/slice97-spring-advisory-linux, including validation.json, *-advisory.json,
*-reply.json and published HTML. Runtime uses arbitrary UID, read-only root, no network,
dropped capabilities and resource limits. Actual bank OCP qualification remains deferred.

## Next logical step

Connect this explicit advisory option to the main Joern scan workflow with bounded candidate
pagination, existing run budgets and exact-attempt report publication. Keep discovery as
the default; propagate stop/skip reasons and policy identity, and prove the full path with
replay before any live-model evaluation. Broader languages' advisory policies, the bank
benchmark, sustained 1,000-repository/day capacity and OCP acceptance remain separate gates.
