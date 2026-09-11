# Slice 66 — Joern coverage accounting without false completeness

The packaged query now emits output contract 2 with graph-represented Java file names
and modeled source/sink/flow counts. The adapter validates counter types/ranges,
flow-count consistency, nonzero endpoints for recorded flows, and graph inventory paths.
It records selected/represented file counts and missing graph files without calling
representation complete parsing.

Discovery observations distinguish:
- modeled flows found;
- no modeled sources or sinks;
- no modeled sources;
- no modeled sinks;
- modeled endpoints with no recorded flow between them.

These describe the narrow query, not all possible vulnerabilities or runtime reachability.
A missing graph file remains visible alongside the observation. Input/build/language
omissions and the narrow model limitations remain unchanged.

Successful process stages are recorded separately from analysis completeness. Until
parser diagnostics are qualified, diagnostic error/warning counts are null rather than
misleading zero values; execution_complete remains false. Derived SARIF does not claim
successful complete analysis. Candidates are retained, status stays partial, and
qualified Joern triage remains unavailable.

Adapter profile experimental-3 and published projection 8 expose discovery_coverage in
shared JSON/HTML/Markdown reports. Historical reports are unchanged. No schema migration.

Validation: 518 tests pass (one existing duplicate-ZIP warning), including all observation
states, missing/foreign graph files, malformed and
inconsistent counters, unknown diagnostics, durable report projection and source-bound
candidate publication. Real seven-case Joern probe and durable renamed/lookalike cases
exercise the new contract. Local macOS testing does not qualify Linux/OCP restrictions.

Next: restricted Linux Joern runtime validation and explicit parser diagnostics, then
the early C#/Rust acceptance gates. No automatic clean verdict, result reuse or LLM call.

Ruff lint/format, whitespace checks and package build pass. Real artifacts are in
`work/slice66-coverage-probe` and `work/slice66-durable`.
