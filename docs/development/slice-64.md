# Slice 64 — Durable experimental Joern Java discovery

Added explicit `joern-java-discover RUN_ID JOERN_HOME` for captured Java snapshots.
The command creates a durable ScanAttempt before tool execution, copies only verified
Java files, runs the packaged fixed Scala query with per-stage process-group timeouts,
and retains original JSON, graph, copied source and logs. Successful output becomes
source-bound SARIF/Candidate records atomically; failures publish no candidates.
No CodeqlAttempt is fabricated. The standard backend registry/scan-run remains CodeQL-only.

The normalizer preserves recorded flow ordering and native Joern rule identity. It rejects
foreign/traversing paths, invalid line references and malformed/oversized results. Snapshot,
copied source and query integrity are checked after execution. It never fabricates omitted
flow nodes. Query code has one canonical packaged location under `traceproof/queries`;
the earlier feasibility runner now uses the same file.

All successful results are partial/discovery-only. This is still the fixture-scoped source
selector `lookup(name)` and name-based executeQuery sink, not qualified Spring/JDBC modeling.
Bundles carry Joern identity and cannot inherit CodeQL evidence policies. No model calls,
automatic reuse or dependency builds are enabled. Network isolation, hard total-memory
limits, comprehensive diagnostics and installed-tool integrity remain unqualified.

Published report projection 7 includes scanner identity and scanner limitations. Original
reports remain immutable; new HTML/Markdown/JSON exports retain the limitations.

Validation:
- Real Joern 4.0.625 / Temurin 22.0.2 macOS ARM64: intake → durable scan → retrieval →
  publication yielded vulnerable/fixed/disconnected candidates 1/0/0, all incomplete.
- Vulnerable candidate produced a source-bound, Joern-tagged evidence bundle with
  unsupported qualified-triage eligibility.
- Unit tests cover invalid references and successful/failed durable publication.
- Full suite: 506 passed (one existing duplicate-ZIP warning); lint/format, whitespace,
  and package build checks pass.
- State and real evidence: `work/slice64-durable`; no migration or bank data required.

Next: replace fixture-specific source/sink selection with bounded Spring/JDBC discovery
models and misleading/safe variants; qualify Joern diagnostics and restricted Linux
execution before broad language claims. C#/Rust acceptance gates remain priorities.
