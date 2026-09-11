# Slice 62 — Backend preparation creation and conservative analysis identity

Pipeline preparation creation now calls the selected backend, completing the creation/
lookup routing boundary for the existing CodeQL implementation. CodeQL profile validation,
offline settings, resource controls and failed-preparation behavior are retained. Joern
is not registered and cannot be selected yet. The preparation result vocabulary and
language profiles still reflect CodeQL and must be adapted for Joern.

New finished static attempts include `analysis_identity`: a deterministic configuration
SHA-256 and explicit `automatic_reuse_eligible: false`. It incorporates scanner engine,
runtime and adapter versions, snapshot, language/scope, preparation tool version/kind,
rule-entry metadata, resources and timeout. Attempt IDs and JSON object ordering do not
change the fingerprint. This is a recorded configuration identity, not a verified content
cache key: transitive rule packs and prepared artifact contents remain unpinned.

There is no automatic analysis-result cache. Existing-attempt skipping remains the
operator retry guard documented in Slice 60; it does not use this fingerprint to claim
identical analysis. Historical records are not backfilled. Unknown versions remain
visible and never become evidence of cache eligibility.

Validation: 499 tests passed (one existing duplicate-ZIP fixture warning), including preparation failure/profile routing, durable scan
outcomes and new engine/version/adapter/rule/snapshot/scope identity regressions. Ruff,
format, whitespace and package build checks run. No migration, live scanner execution,
container rebuild or LLM call.

Next logical slice: pinned Joern feasibility/adapter vertical slice for Java, defining its
prepared result and evidence normalization explicitly. Keep automatic result reuse
disabled while rule-pack and artifact pinning are incomplete. CodeQL policy isolation is
already enforced; Joern remains discovery-only until separately qualified. Full rule-pack
pinning is required before enabling automatic reuse, rather than blocking a no-cache
Joern POC.
