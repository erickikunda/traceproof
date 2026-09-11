# Slice 61 — Prepared-input lookup and engine-scoped evidence policies

The selected backend now resolves its durable prepared input. CodeQL database lookup
and successful-extraction validation moved out of generic scan orchestration into the
CodeQL backend boundary. Preparation creation remains CodeQL-specific; this does not
introduce Joern or a generic graph store.

Bundle builder 6 records engine identity from the trusted attempt metadata. Historical
CodeQL attempts without scanner metadata are identified as legacy CodeQL; explicitly
missing/malformed identity is unknown. Existing bundles from builders 1–5 (including
the original unversioned schema) retain legacy CodeQL compatibility. New bundles with
missing engine identity cannot qualify under CodeQL policies.

Evidence gate 8 scopes policies to the engine as well as the native rule identifier.
Triage eligibility and provider requests apply the same engine check. Copying a CodeQL
rule name into Joern/Opengrep output does not grant qualified advice. Unknown engines
remain unsupported. Prompt version 3 and the gate/builder versions distinguish the new
behavior in existing identity/cache contracts. No automatic finding verification or
suppression is introduced.

Validation: 491 tests passed (one existing duplicate-ZIP fixture warning), including existing source/flow qualification and persisted
gate tests, plus cross-engine rule-name collision and missing-identity regressions.
Ruff lint/format, whitespace checks and package build run. No live engine/container test
or model call is required for this routing/policy change; no database migration.

Remaining S2 work: preparation creation routing, complete engine/rule-pack/version reuse
identity, and normalized evidence/output contracts for a non-CodeQL backend. Then a
pinned Joern Java/Spring vertical slice. Only CodeQL is runnable today.
