# Slice 104 — Bounded C/C++ argv-to-system advisory

## Outcome

Explicit `joern-c-argv-review-v1` and `joern-cpp-argv-review-v1` policies enable evidence
checks, budgeted triage and the main scan/advisory/report workflow for the existing
`c-family-argv-system-v1` discovery profile. Default scanning remains discovery-only.
No migration, Redis service, live provider key or HTTP launch-schema change is required.

## Evidence contract and limits

The isolated syntax parser accepts a global int main with two parameters, a char** or
char*[] argv parameter, and a positive decimal literal subscript. Sink evidence requires
a direct, single-argument system call and an explicit <stdlib.h> include. Obvious local
bindings, argv writes, non-main sources and unsupported endpoint shapes cannot qualify.
Source and sink claims must bind to the exact retained native endpoint, source hash,
line and complete quote. Native/query/SARIF integrity and complete retained file context
are required before provider invocation. Guards remain unknown and negative dismissal is
unsupported. Passing advice is needs_review, unverified, with incomplete reporting.

This is bounded syntax analysis: it does not preprocess includes, compile code, establish
libc ownership, resolve general C++ semantics or prove attacker control/runtime reachability.
Macros and preprocessing directives other than includes are withheld; namespaces, classes,
templates and lambdas are outside the accepted context. Header contents can change semantics
without being resolved by this gate. C++ acceptance covers C-style .cpp examples, not all
C++ constructs or extensions. The existing source-copy suffix limits remain in force.

Parser limits are 1 MiB input, 50,000 syntax nodes, five CPU seconds, ten-second subprocess
timeout and 512 MiB Linux address space. No source builds or execution occur in the parser.
Builder version 13 retains small registered C/C++ source/header files within existing byte
limits. Native paths retain the existing 2–7 node limit; truncated evidence is withheld.

Added hash-locked tree-sitter-c 0.24.2 and tree-sitter-cpp 0.23.4:
[C package](https://pypi.org/project/tree-sitter-c/),
[C++ package](https://pypi.org/project/tree-sitter-cpp/). Bank package approval remains separate.

## Validation

59 new regression tests cover isolated parsing, misleading endpoints, limits, evidence
integrity, explicit policy selection, budget stops, idempotency and scan/report integration.
The full suite passes: 947 tests, with one existing duplicate-ZIP fixture warning.
Lint, formatting, whitespace and package build checks pass.

Both restricted ARM64 Linux suites pass: eight cases per language, 56.052 seconds for C
and 58.022 seconds for C++. Image:
sha256:e8b52d9a2549b3f1174a6b1ac5918dae60fe74e51c0f9c48ab8c14af5da82153.
Artifacts: work/slice104-argv-c-linux and work/slice104-argv-cpp-linux.

Each suite covers vulnerable/fixed, cross-file vulnerable/fixed, disconnected, renamed,
non-main and local-system fixtures. Twelve native scans per language include the initial
eight cases, a fixed rescan and three positive advisory rescans. Each language records
three replay calls, zero live calls and 420 simulated micro-USD. Repeat imports add no calls.
Synthetic replies validate orchestration, not model judgment or bank benchmark recall.
Arbitrary UID, read-only root, disabled network, dropped capabilities and resource limits
were enforced. Actual OCP acceptance remains deferred; ocp_qualified is false.

## Next logical work

Complete a POC readiness and integration-gap checkpoint across the supported language/profile
matrix. Use it to select the next incomplete end-to-end requirement before further CLI polish
or deeper local language refinements. Bank benchmark quality, live-model evaluation,
sustained 1,000-repository/day throughput and actual bank OCP execution remain open gates.
