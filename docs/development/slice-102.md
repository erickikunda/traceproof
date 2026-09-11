# Slice 102 — Bounded Go HTTP-to-shell advisory

## Outcome

The explicit joern-go-http-review-v1 policy enables evidence checks and budgeted advisory
for the go-http-shell-v1 Joern discovery profile. It works with check-evidence, triage,
triage-attempt and the main scan/advisory workflow, including exact-attempt report retrieval.
Default scans remain discovery-only. No migration or live provider is required for replay.

The existing ledger, run budgets, request/page caps, provider controls and idempotency are
reused. Unsupported or incomplete evidence blocks calls; advice can be needs_review or
abstain. Negative verdicts and present-guard claims remain unsupported. Reports stay
partial/incomplete and unverified, including zero-candidate reports.

## Evidence scope

An isolated Tree-sitter Go parser checks explicit interpreted-string imports of net/http
and os/exec, including simple aliases. Sources are single-line FormValue/PostFormValue
calls with one interpreted-string key on a named *http.Request function parameter. Sinks
are single-line exec.Command calls with exactly three arguments: literal sh, bash, /bin/sh
or /bin/bash; literal -c; and command text. The claim must quote the full Command call,
not just the third argument. Native source/sink code must match these parsed expressions.

File-wide binding/write inventories conservatively reject conflicting imports, obvious
shadowing/rebinding, and repeated request-parameter names. Calls on fake types/packages,
normal process arguments, dynamic shell/flag expressions and variadic command arguments do
not qualify. Raw-string and dot imports, request aliases/local initialization, method
receivers, function-literal handlers and more complex shapes are outside this bounded gate.
It is not general Go type resolution, cross-file symbol resolution or package authentication.

The policy requires the pinned native/query/SARIF/source relationship, all 2–7 literal path
nodes and complete retained file context. Builder version 11 retains small Go files for
registered Joern policies within existing 16 KiB source / 32 KiB envelope limits. Larger
files require complete reconstruction from bounded excerpts. Parser limits remain 1 MiB,
50,000 nodes, five CPU seconds, ten-second subprocess timeout and 512 MiB Linux address
space. Scanned application code and dependencies are neither built nor executed by the
syntax check. Incomplete context, ambiguous endpoint lines and unsupported imports abstain
before invocation.

The native flow and syntax establish a recorded request-input-to-shell-command construction
candidate. They do not establish route exposure, command execution, guard effectiveness or
exploitability. The checker does not require or certify Run/Start/Output after construction.
That distinction remains visible in the scan limitations and advisory contract.

## Dependencies and validation

Added tree-sitter-go 0.25.0 to the project/uv lock and regenerated hash-pinned container
requirements. The acceptance image installs locked parser binaries at build time; runtime
validation is offline. Bank builds must obtain these through approved package sources.
Package reference: [Tree-sitter Go](https://pypi.org/project/tree-sitter-go/).

844 tests pass (one existing duplicate-ZIP fixture warning). Lint, format, whitespace and
package build checks pass. All nine restricted Linux cases pass in 66.555 seconds.
ARM64 image: sha256:206a69230eb9a02e514c302b332717e614772324275e557abcc1b810c05eb962.
Artifacts: work/slice102-go-advisory-linux-final. Runtime uses arbitrary UID/GID 0, read-only
root, no network, dropped capabilities and bounded resources; ocp_qualified remains false.
Three replay invocations and zero live calls were recorded. An earlier run also passed;
the final image additionally rejects unsupported raw imports before endpoint inventory. Tests cover isolated parsing, aliases,
misleading imports/types, shadowing/writes, unsupported shell shapes and input bounds,
native/context/quote failures, negative verdicts, zero-call evidence/budget stops,
idempotency, CLI policy selection and main scan/report integration. Unit native paths are
synthetic contracts; the separate Linux runner exercises actual Joern output.

Native acceptance covers nine cases: vulnerable/fixed, cross-file vulnerable/fixed,
disconnected, renamed imports/request with PostFormValue, fake request, non-shell command
and fake sink. Three positive cases each produce one replay needs_review advisory; six
negative cases produce no candidates. The runner performs thirteen native scans: nine
initial scans, one fixed rescan and three positive advisory rescans. It creates deterministic
fixture responses from the first bundles and replays them against new attempts, validating
exact report retrieval, retry suppression and accounting (420 simulated micro-USD total).
This tests orchestration/contracts, not model judgment, bank precision/recall or fleet speed.

## Next logical work

Add bounded advisory for the existing Rust environment-to-shell profile, requiring its own
native/source/endpoint acceptance. Then address C-family advisory and remaining coverage
gaps. Preserve breadth over additional CLI polish. Live-model quality, the bank benchmark,
sustained 1,000-repository/day capacity and actual bank OCP execution remain open gates.
