# Slice 84 — Python durable Joern integration

Applied the approved breadth-first priority: further C# source-profile refinement is
deferred. Python now has an explicit joern-python-discover command using the shared
scan lifecycle, source-only preparation, bounded packaged query, graph inventory,
SARIF normalization, persistence and normal report retrieval/publication.

The profile selects lookup(input) to the first argument of calls named system. It is
an integration baseline, not general Python framework or command-injection coverage.
Call names do not authenticate API identities. Reports remain partial/non-adjudicated;
qualified triage remains unsupported. No automatic backend routing or result reuse was
introduced. Existing Java defaults and repaired C# entry points are preserved. Invalid
language/repair combinations are rejected before touching tooling or creating scans.

A new offline image layer and joern-python acceptance suite reuse the five existing
fixtures. Real restricted Linux ARM64 acceptance passed in 25.996 seconds:
single-file vulnerable/fixed 1/0, cross-file vulnerable/fixed 1/0, disconnected 0.
Every recorded flow snippet matched its reported source line; expected source files
were represented in the graph. Durable report retrieval and publication remained
incomplete, and evidence bundles retained unsupported qualified-triage eligibility.
Source-line assertions are fixture evidence, not a new general span-verification system.

Image: `sha256:0d9d05ad979a57a2b8965867a346494e2f710ff6be89039bb7c720dd77abf18c`.
Artifacts: work/slice84-python-linux. Runtime uses arbitrary UID, read-only root,
no network, dropped capabilities, no-new-privileges and CPU/memory/PID/tmpfs limits.
No LLM calls or application builds. This timing is a fixture run, not a capacity estimate.

542 tests passed (one existing duplicate-ZIP warning). Shared lifecycle success/failure
tests now cover Python; three invalid-profile combinations are tested. Lint, formatting,
package build and whitespace checks pass. No migration or user action required.
Changes remain uncommitted. Next JavaScript/TypeScript durable integration and the same
minimum Linux acceptance, followed by Go and Rust; C/C++ remains planned follow-on.
Broader detection and the 50-repository benchmark remain separate work, as does bank OCP.
