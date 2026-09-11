# Slice 90 — Joern benchmark coverage audits

The existing evaluator was limited to two Python CodeQL rules and qualified completed
reports. Added a separate schema-2 Joern discovery_coverage_audit plan without relaxing
that gate. It pins the benchmark manifest, published query digest, scanner version,
standard profile, one known Joern rule and exact report IDs. All nine current bounded
Joern rule identities are accepted. Internal CWE associations describe intended scope,
not detection qualification. Schema-1 CodeQL plans and evaluator-version-2 output retain
their behavior; new Joern audits use evaluator version 3.

Joern audits retain every label and report candidate, disclose missing reports plus
scanner/query/version/language mismatches, and mark labels not_evaluable under current
unqualified discovery profiles. Candidates remain unjudged. Recall values, precision
and confirmed recall remain null; incomplete audits cannot yield comparison deltas.
The label denominator is retained, but these audits are not zero-recall measurements.
No location-match credit or false-positive adjudication is inferred from raw candidates.

Repository JSON/CSV includes scanner identity, language, discovery coverage and scanner
limitations alongside scope gaps. HTML identifies coverage audits and displays recall
as not evaluable. Existing Markdown/CSV publication and immutable retrieval work without
migration. Evaluator inputs remain separate from scan workers; no scans or LLM calls
are dispatched by evaluation.

Real validation used the retained synthetic Rust vulnerable scan from Slice 87. The
independently specified shell-input label remained not_evaluable, the existing candidate
remained visible/unjudged, query/engine/version/language checks agreed, and the audit
published and retrieved identically. Artifacts: work/slice90-evaluation; repeatable helper
scripts/validate_joern_evaluation.py. No bank ground-truth data was used.

596 tests passed (one existing duplicate-ZIP warning), including all profile identities,
unknown/cross-engine rules, missing reports, null-metric dashboard exports and legacy
CodeQL evaluation behavior. Lint, formatting, package build and whitespace checks pass.
No migration or user action needed. Changes remain uncommitted.

This completes compatibility for explicit coverage audits, not a Joern recall evaluator.
Next prioritize useful discovery-profile expansion beyond fixture-specific source/sink
names and an explicitly scoped exploratory location-match evaluation, keeping incomplete
coverage separate from confirmed vulnerability metrics. The 50-repository benchmark,
adjudication, throughput and bank OCP remain future validation gates. Avoid spending
further slices on CLI polish before those detection goals.
