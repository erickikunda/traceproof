# Slice 60 — Explicit scanner identity and prepared-input provenance

New static-attempt JSON includes `scanner` (engine, adapter and runtime versions, output
format and bounded capabilities), `prepared_input` (engine/kind, extraction identifier,
run/snapshot and preparation tool version), and `rule_entry` (engine, entry SHA-256 and
explicitly unverified transitive dependencies). Existing CodeQL fields remain intact.
These records identify preparation; they do not claim the database itself was hashed.
Capability declarations describe possible output, not per-finding evidence or verified
coverage. Native SARIF rule identities and candidate fingerprints remain unchanged.

A trusted Python backend registry routes query execution. Only CodeQL is enabled.
Internal `scan_run` and `analyze` reject other engine selections before store access;
there is no user-facing Joern option or dynamic plugin loading. Preparation remains
CodeQL-specific pending the next adapter work.

The existing-attempt guard now excludes explicitly different engines. Historical
attempts lacking engine metadata retain the legacy CodeQL interpretation only in this
CodeQL-owned attempt store; reports are not retroactively rewritten. This guard remains
an operator retry safeguard, not a content-addressed cache: use explicit rescan after
changing tools or rules. Full engine/rule-pack/version-aware reuse remains required
before multiple backends are enabled.

Validation: full suite 486 passed (one existing duplicate-ZIP warning), Ruff lint/format,
whitespace check and package build. Tests cover provenance round-trip for all existing
execution outcomes, unsupported backend rejection before side effects, cross-engine
skip isolation, and the existing historical skip behavior. No live scanner/container
qualification was performed for this metadata change. No migration or model call.

Next: finish S2 prepared-input routing and engine-aware evidence/policy qualification,
then introduce pinned Joern execution and a Java/Spring fixture. No new backend may
inherit CodeQL triage qualification by copying its rule IDs or matching CWE labels.
