# Slice 15: CLI operator guide and documentation delivery gates

The [CLI user/operator guide](../guides/cli-operator-guide.md) consolidates the implemented
laptop workflow into task-oriented instructions. It covers installation/state selection,
identifier handoffs, local CSV/archive intake, Python indexing, CodeQL, evidence and
offline/live triage, budgets, operator review, report selection/sharing, benchmarks and
recovery. It explicitly distinguishes recorded success from security completeness.

The implementation plan now requires an API companion guide with the first hosted API,
in addition to generated OpenAPI, and guide updates for user-visible changes. API routes
are not documented as available before they exist. Multiworker and OpenShift runbooks
extend the guides at M5/M6.

Validation uses isolated synthetic state: current command help, local intake/indexing,
real CodeQL vulnerable/fixed/incomplete acceptance, replay idempotency, review publication,
selection, five report formats and unchanged exact historical retrieval. No provider
credentials, paid requests or bank data are needed. Validation artifacts are local under
`work/slice15-guide-validation`; they are not source-controlled product fixtures.

Results: 60 CLI checks passed; all three real CodeQL acceptance cases passed using
CodeQL 2.27.0 in 14.92 seconds. Documentation links and whitespace checks passed. The
runtime suite was not repeated for these documentation-only changes.

This is a documentation slice: no runtime behavior or schema changes. Schema remains
0006. Full-plan delivery credit stays unchanged; useful operator documentation does not
establish benchmark quality, enterprise compatibility or fleet throughput.
