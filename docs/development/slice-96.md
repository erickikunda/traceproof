# Slice 96 — Explicit Java/Spring Joern evidence review gate

## Outcome

An explicitly selected joern-spring-review-v1 policy can now assess a saved needs_review
decision against a fresh, source-bound Java/Spring Joern evidence bundle. The policy is
available through check-evidence --review-policy and the development assessor. It invokes
no provider and does not persist a triage verdict, suppress candidates or enable automatic
Joern model calls. Shared requirements remain CodeQL-only.

The existing Java quote, annotation, SQL-call and retained-path checks are reused through
a common helper. The Joern engine identity is retained; the bundle is not relabeled as
CodeQL. Negative suggestions remain unsupported. Passing means supported_for_review,
with unknown guards/reachability and no claim of exploitability or runtime type identity.

## Native evidence binding

New scans record the flows.json digest. Bundle builder version 7 adds an audit for the
bounded Spring rule: pinned Joern version and packaged query digest, unchanged native
output, byte-consistent regenerated SARIF, unique native path, and native code present
on each snapshot-bound source line. The audit retains the ordered path, source hashes and
native/query/SARIF identities. Historical bundles remain immutable/readable; older scans
without a native digest cannot silently acquire review eligibility and need a new scan.

The review gate then requires the retained bundle path to match every audited node and
reconstructs complete, consistent source files whose hashes match the audit before running
the shared Java claim checks. Changes to provenance, quotes, topology, context or code
withhold eligibility. Missing/ambiguous paths and synthetic or multiline node text are
not repaired by inference. The audit is coordinate/provenance consistency, not proof that
the graph's inferred edges are semantically correct.

Limits: one path of two to seven nodes, native output bounded to 16 MiB, node code to
2,000 characters, source file to 1 MiB during audit, and the existing 32 KiB bundle/16 KiB
source-context limits. Full source context is required for all path files. Unknown
framework/dependency identity, sanitizer semantics, completeness and runtime reachability
remain explicit. No bank recall or true-positive qualification follows from this gate.

## Validation

Seven fresh restricted Linux cases passed in 49.243 seconds: vulnerable and renamed
cross-file flows (one candidate each), fixed, disconnected, annotation lookalike, sink
lookalike and unmapped route (zero candidates). The positive bundles pass the explicit
policy using deterministic synthetic claims; these are not LLM quality measurements.
The fixed fixture also receives an explicit rescan, for eight native scans. Existing
report publication, retry suppression and unsupported automatic-triage checks pass.

Image: sha256:897d1473fecb5c177ba4c741719d43cc14a1922fdf0a465ce05d1758ef59a723.
Artifacts: work/slice96-spring-evidence-linux, including validation.json and *-gate.json.
Runtime: arbitrary UID, read-only root, disabled network, dropped capabilities and resource
limits. The CLI policy selector was added after this native run and is tested locally;
the native audit and shared gate implementation used by the image are unchanged.

Full automated suite: 654 tests pass, with one existing duplicate-ZIP fixture warning.
Ruff and diff whitespace checks pass.

Unit/integration controls reject missing provenance, scanner/query/SARIF mismatches,
altered native coordinates and code, path reorder/truncation, missing/foreign context,
fabricated quotes, negative decisions and historical attempts without native hashes.
CodeQL evidence behavior and default Joern rejection remain covered.

## Next logical step

Wire this policy into an explicit opt-in, budgeted advisory path with replay-provider
acceptance first. Check native/context eligibility before spending tokens, preserve
provider/model/policy identities and cache boundaries, and keep default Joern discovery
unchanged. Live provider use still requires existing operator configuration and source
transmission controls. No new confirmation, migration or bank data is needed for local
replay testing. Actual OCP, representative throughput and ground-truth gates remain open.
