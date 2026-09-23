# Slice 108 — Specialized C# and Rust mounted-input handoff

Added separate digest-pinned C# and Rust smoke layers around the common offline entrypoint.
Each packages only its language allowlist and defaults to that language. The manifest
renderer accepts all nine selections; runtime validates against its image-specific list.
The general image still excludes C#/Rust. No extra tool paths come from CSV metadata.

C# passes /opt/veriflow/csharp-repair to the existing repaired-frontend identity gate;
Rust passes /opt/rust to the existing trusted-toolchain gate. Neither gate is bypassed or
replaced. Failure is propagated and recorded without fallback or provider calls. The
specialized layers preserve their qualified base application snapshots (Slices 101/103),
while the general smoke layer uses Slice 104. They are not a unified release image.
Upgrades require explicit base rebuilding and requalification.

C# uses the bounded repaired Lookup/CommandText model; native mounted acceptance uses the
ASP.NET Core vulnerable/fixed fixture. Rust uses the restricted dependency-free Cargo
environment-to-shell profile. This extends deployment integration, not framework/CWE coverage.
No automatic advisory, migrations, bank deployment or image pushes are involved.

Local image digests:
- C#: sha256:21a60b4d567572440c130feb3429e17bf2968e80eac58045cd9333313d59baf4
- Rust: sha256:17ebb7d6953208171ec03434e16070bdc065b6c55a425d2fb58e12f221b695b1

Validation artifacts: work/slice108-smoke-csharp and work/slice108-smoke-rust. Both use the
same arbitrary-UID, read-only-root, no-network Docker rehearsal and exact JSON/HTML report
checks. Results remain partial; actual OCP/AMD64/PVC/SCC acceptance stays deferred.

Tests additionally exercise fixed tool-path dispatch, propagation of a rejected tool identity,
zero model calls and early wrong-image language rejection. Existing underlying repair and
Rust toolchain regressions remain part of the full suite. Both native vulnerable/fixed pairs pass (four scans, 1/0 candidates per language),
with exact JSON/HTML report exports and zero model calls. The full suite passes 969 tests
with one existing duplicate-ZIP fixture warning. Lint, formatting and whitespace checks pass.

Next logical work: address the remaining repository-URL acquisition gap from the POC
checkpoint with explicit bounded intake and offline scanner separation. Bank source access,
live gateway, representative ground truth and actual OCP remain separate acceptance gates.
