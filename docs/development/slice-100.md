# Slice 100 — Bounded Express advisory for JavaScript and TypeScript

## Outcome

Two explicit policies now support the existing express-request-eval-v1 Joern profile:
joern-javascript-express-review-v1 and joern-typescript-express-review-v1. They work with
check-evidence, triage, triage-attempt and the main scan/advisory workflow. Defaults remain
discovery-only; no migration or live model call is required for replay validation.

Each policy requires the matching language, rule, profile and packaged query digest.
Native output is hash-bound, regenerated SARIF must match the retained result, and all
2–7 path nodes must match source lines and complete retained context. Builder version 9
retains small JS/TS files for registered Joern policies within the existing 16 KiB source /
32 KiB bundle limits. Unlike the Flask policy, nonliteral native intermediates are withheld.

## Endpoint checks and limits

An isolated Tree-sitter parser inventories bounded syntax without installing repository
packages or executing source. Limits: 1 MiB input, 50,000 nodes, five CPU seconds, ten-second
subprocess timeout and 512 MiB Linux address space. Advisory context is further bounded by
the evidence envelope and complete-file reconstruction. Syntax/encoding/parser failures
and incomplete context cannot qualify for a provider call.

The supported shape is a top-level default Express import, a const application initialized
by its no-argument factory call, and get/post with a literal route and inline two-parameter
handler. The first handler parameter supplies a static query/body/params field access.
Direct single-argument eval is the sink. Each endpoint must be unique on its source line;
the native sink argument must match the parsed eval argument, and the claim must quote the
full eval call. File-wide binding/write checks conservatively reject obvious rebinding,
shadowing and conflicting names. Comments, strings, computed/optional request access,
member/optional eval and multiple eval arguments do not qualify.

This intentionally does not implement general JavaScript name resolution or runtime package
identity. CommonJS factories, Router/middleware patterns, named handlers, multiple handlers
sharing a parameter name, JSX/TSX and ambiguous endpoint lines are outside the bounded gate.
Joern's previously documented factory-import-alias gap remains. Typed TypeScript handler
parameters have parser-level tests; native fixtures exercise the existing .ts corpus and
do not establish broad typed-framework coverage.

The only positive advisory disposition is needs_review. Guards remain unknown, negative
verdicts/present-guard claims are unsupported, and reports stay incomplete and unverified.
Native paths do not prove execution, sanitization, route exposure or exploitability.
Existing run budgets, request/page caps, reservations, policy-aware idempotency, provider
controls, retry suppression and exact-attempt report retrieval are reused.

## Dependencies and packaging

Added tree-sitter-javascript 0.25.0 and tree-sitter-typescript 0.23.2 to the project and uv
lock. The exported hash-pinned container requirements are updated. The acceptance layer
installs locked binary dependencies at image build time; runtime validation has no network.
Bank image builds can supply these packages through their approved package mirror. This
slice does not test that mirror or assert enterprise approval.

Package references: [JavaScript grammar](https://pypi.org/project/tree-sitter-javascript/)
and [TypeScript grammar](https://pypi.org/project/tree-sitter-typescript/).

## Validation

760 tests passed (one existing duplicate-ZIP fixture warning). Lint, format, diff whitespace
and package build checks passed. Native acceptance passed all 16 cases: JavaScript in
61.141 seconds and TypeScript in 68.493 seconds. Each suite runs 12 native scans (eight
initial, one fixed rescan, three positive advisory rescans), makes three replay calls and
zero live calls, and accounts for 420 simulated micro-USD, not an external charge.

Both use ARM64 image
sha256:3825d9023644599da2a2cbd880de973e4f2933da48e6a07e04a863e4c34b28ea.
Artifacts: work/slice100-express-javascript-linux-final and
work/slice100-express-typescript-linux-final. Runtime: arbitrary UID/GID 0, read-only root,
no network, dropped capabilities and bounded resources. ocp_qualified remains false.

An initial harness dispatch error selected the discovery runner for the new suite name;
that failed before scanning and was corrected. Parser tests also caught the distinct
TypeScript optional-call token; both optional-call representations now fail closed before
the successful native runs. Initial diagnostics remain in work/slice100-express-javascript-linux.
Unit coverage includes both languages, typed TS syntax, misleading/shadowed endpoints,
parser bounds, evidence tampering, complete-context requirements, full-call quotes, negative
verdict rejection, zero-call evidence/budget stops, idempotency and scan/report integration.

The native runner exercises eight cases per language: vulnerable/fixed, cross-file
vulnerable/fixed, disconnected, renamed handler/application, fake import and member eval.
Each positive is rescanned through the advisory workflow using a deterministic response
constructed from the initial fixture bundle. This validates contracts/orchestration, not
live-model judgment. Repeat imports do not add calls; report IDs retrieve the intended
advisory snapshots. Five negative cases per language produce zero candidates; this fixture
result does not imply application safety or measured recall.

## Next logical work

Add bounded advisory for the repaired C#/ASP.NET Joern profile using its existing
source-location evidence and syntax checks. Use minimum positive, fixed and misleading
acceptance, keeping broader discovery/framework gaps explicit. Continue language breadth
over CLI refinement. Go, Rust and C-family advisory, live-model quality, the bank benchmark,
fleet throughput and target OCP execution remain separate gates.
