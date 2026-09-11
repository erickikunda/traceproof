# Slice 92 — Express HTTP-input discovery for JavaScript and TypeScript

## Outcome and scope

A shared opt-in `express-request-eval-v1` profile removes dependence on fixture function
names for a bounded Express pattern. The main scan-run/scan-import workflow and both
standalone language commands accept it. No database migration or LLM key is required.
Default profiles remain unchanged.

Joern identifies Express get/post route calls and the inline second-argument handler.
The source selector links the first handler parameter by graph reference to field reads
of query/body/params, for example `incoming.query.code`. The sink selector requires the
builtin eval graph signature. The graph provides the flow between these endpoints;
TraceProof does not invent intermediate edges. Profiles have distinct rule identities,
query digests, published profile metadata and retry suppression. Existing source-location,
report retrieval, evidence and benchmark coverage-audit paths remain in force.

## Acceptance

Eight cases per language: direct vulnerable/fixed, ES-module cross-file vulnerable/fixed,
renamed request/application variables with a POST body source, unregistered handler,
fake Express import and member eval lookalike. Expected counts are 1/0, 1/0, 1, 0, 0, 0.
Cases also verify graph inventory, endpoint source coordinates, persisted report retrieval,
publication, batch retry suppression and unsupported qualified triage. Fixed input is
explicitly rescanned to verify a fresh attempt. No model calls occur.

Full automated suite: 615 passed (one existing duplicate-ZIP-entry fixture warning).
Ruff and diff whitespace checks pass. Native acceptance uses the same immutable ARM64
image in restricted Linux: arbitrary UID, no network, read-only root and resource limits.
JavaScript passed in 49.377 s and TypeScript in 48.082 s (nine scans per suite).
Image: `sha256:5332cc64fe0ce66eb6441bb0e7fe72be5bc835286424166a1030da8c617ee6eb`.
Artifacts: work/slice92-express-javascript-linux-final and
work/slice92-express-typescript-linux, including validation.json and shareable reports.

## Observed limits and deliberate stopping point

The native probe found no flow when the whole request parameter or intermediate query
object was selected. Selecting the actual field read yielded the recorded flow. Deeper,
computed or destructured accesses are not accepted by this profile.

The initial Express factory import-alias fixture was missed because the frontend graph
signature changed. Its failed acceptance artifacts are retained under
work/slice92-express-javascript-linux. The final renamed-variable fixture retains the
standard factory import; import aliases are explicitly not qualified. This is a known
recall gap, not a repaired case or a claim that factory aliases are safe.

Routers, middleware, named callbacks, mixed JS/TS, JSX/TSX, dependency/module identity,
dynamic mutations and sanitizer semantics remain outside acceptance. Graph signatures
are not runtime identity or exploitability proof. Reports remain partial/discovery-only;
zero findings are not a clean verdict, qualified triage is unsupported and benchmark
recall/precision remain unknown. Bank OCP validation remains deferred.

## Next logical work

Expand Go beyond lookup(input) with a bounded HTTP-request source profile, preserving
process-argument evidence separately from a claim of shell command injection. Prioritize
useful language breadth before returning to Express import aliases or deeper modeling.
