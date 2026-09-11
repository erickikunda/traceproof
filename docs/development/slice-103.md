# Slice 103 — Bounded Rust environment-to-shell advisory

## Outcome

The explicit joern-rust-env-review-v1 policy enables check-evidence, triage, triage-attempt
and main scan/advisory integration for rust-env-shell-v1. The existing trusted Rust
installation and strict dependency-free, single-binary Cargo preparation contract remain
required. No migration or live model key is needed for replay validation. Defaults remain
discovery-only, and the budget/request/page/idempotency/report workflow is reused.

## Evidence and syntax bounds

The isolated Rust parser recognizes std::env::var with one ordinary string-literal key and
a direct Command::new(literal shell).arg("-c").arg(command) chain. The supported shell names
are sh, bash, /bin/sh and /bin/bash. Simple top-level use imports of std::env::var or
std::process::Command, including aliases, are checked against a conservative file-wide
binding inventory. Fully qualified calls are accepted only without a local std binding.
Duplicate/conflicting aliases, obvious declaration shadows, grouped/wildcard/nested imports,
macros and conditional attributes cannot qualify for this bounded gate.

This is not a Rust compiler, general name resolver, macro expander or lifetime/trait
analysis. More complex namespace, closure or pattern semantics remain unqualified. Raw
string keys, indirect constructors, args collections, extra builder operations between the
shell/flag/command calls, and nonliteral shell/flag shapes are outside the accepted endpoint
syntax. Native graph signatures and source checks do not prove standard-library ownership
under every Rust construct.

Native/query/SARIF/source integrity and complete retained file context are required. Every
retained native code node must be literal on its recorded source line. Rust environment
paths may contain 2–8 nodes: the existing cross-file fixture has eight, so this profile
retains nine locations including the primary location. Other profiles keep their previous
limits. No intermediate nodes are discarded to manufacture eligibility. Builder version 12
retains small Rust files for this registered profile, within the existing 16 KiB source /
32 KiB envelope limits. Larger/truncated evidence stays unsupported.

The parser uses the same limits as the other bounded endpoint parsers: 1 MiB input,
50,000 nodes, five CPU seconds, ten-second subprocess timeout and 512 MiB Linux address
space. It does not compile source, execute build scripts or expand macros. Claims must quote
the environment call and full command construction chain through the final arg call, not
just the command argument. Guard claims remain unknown; negative dismissal is unsupported.

Environment input is not automatically attacker-controlled. Command construction is not
proof of execution, and status/spawn/output calls are not certified by this gate. Passing
advice is needs_review, with incomplete/unverified reporting. Unmodeled context and missing
evidence block calls rather than creating a clean verdict.

## Dependencies and validation

Added tree-sitter-rust 0.24.2 and updated the uv/hash-pinned container requirements.
[Package reference](https://pypi.org/project/tree-sitter-rust/). The image uses the previously
qualified Rust UBI 10 base and installs locked grammar binaries at build time. Runtime is
offline. Approved package sourcing and bank OCP acceptance remain separate work.

888 automated tests pass (one existing duplicate-ZIP fixture warning), along with lint,
format, whitespace and package build checks. All nine restricted Linux cases pass in
90.239 seconds, on ARM64 image
sha256:357f345efc791b0da986aeb39d04fa57f682d53043412f3d8ee2ccfbc205e723.
Artifacts: work/slice103-rust-advisory-linux-final. Arbitrary UID/GID 0, read-only root,
no network, dropped capabilities and bounded runtime resources were enforced.
Three replay advisories, zero live calls; ocp_qualified remains false. Unit checks cover isolated parsing, aliases,
misleading endpoints and shadows, unsupported macro/import/attribute context, parser limits,
complete native evidence, the real eight-node cross-file path, budget/evidence stops,
idempotency, CLI policy checks and main scan/report integration.

The native runner exercises nine cases: vulnerable/fixed, cross-file vulnerable/fixed,
disconnected, renamed imports, fake source, non-shell command and fake sink. It creates
synthetic replies from initial fixture bundles and replays them against new attempts;
this tests contracts/orchestration, not live model judgment. Thirteen native scans include
nine initial cases, one fixed rescan and three positive advisory rescans. Successful runs
produce three replay needs_review advisories, zero live calls and 420 simulated micro-USD
of ledger accounting. Repeat imports add no calls. Zero candidates in the six negative
fixtures do not establish safety or measured recall.

The initial Linux run exposed the eight-node cross-file path and correctly withheld its
truncated bundle before provider invocation. The Rust-only allowance now retains the whole
path and has a regression test; paths beyond the allowance remain ineligible. Initial
diagnostics are retained in work/slice103-rust-advisory-linux.

## Next logical work

Add bounded advisory for the existing C/C++ argv-to-system profile, keeping C++ call identity
and unresolved semantics explicit. Then assess remaining POC coverage/integration gaps,
with bank benchmark quality, live-model evaluation, sustained 1,000-repository/day capacity
and actual bank OCP execution still separate acceptance gates. Prefer overall completeness
to further CLI refinement or exhaustive local language perfection.
