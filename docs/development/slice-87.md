# Slice 87 — Rust durable Joern integration

Added joern-rust-discover with the bounded lookup(input)/arg argument-1 profile,
archive-to-scan persistence, candidate retrieval, report publication and Joern bundle
gating. The operator supplies trusted Joern and standalone Rust/rust-src toolchains.

The preparation boundary accepts only a dependency-free root Cargo.toml with package
name/version/edition, optional build=false, and one explicit binary name/path. Other
manifest sections/settings, dependencies, workspaces and custom build hooks are rejected
before scanning. Rust sources are copied and a restricted Cargo manifest is generated
with build scripts and all automatic target discovery disabled. Repository Cargo config
and toolchain files are omitted. Generated metadata is hashed and rechecked after scanning.
Cargo uses an isolated home and offline mode. This is a deliberately narrow admission
profile, not support for arbitrary Rust projects or an OS sandbox by itself.

An actual Linux failure identified an upstream binary compatibility requirement:
Joern 4.0.625's Rust AST generator requires GLIBC 2.39 and cannot execute on the existing
UBI 9 base. The initial run emitted an empty graph; the acceptance check rejected it.
Rust scans now explicitly fail if the graph contains none of the selected source files.
A dedicated digest-pinned UBI 10 Python 3.12 Minimal runtime resolves the compatibility
issue without changing Joern or the other language images. Locked Python dependencies,
JDK and Joern come from the trusted local base; this transfer was exercised end-to-end.
Rust 1.98.1 and matching rust-src archives are verified against official release hashes
recorded in scripts/joern/rust-linux-toolchain.json. Actual bank image approval remains open.
Official base reference: https://catalog.redhat.com/en/software/containers/ubi10/python-312-minimal/677d315be3c3dff7ee21a2ee

Five real cases passed on macOS and restricted Linux ARM64: single-file vulnerable/fixed
1/0, cross-file vulnerable/fixed 1/0, disconnected input 0. All retained snippets matched
reported source lines; selected fixture files appeared in graph inventory. Reports
remained incomplete and qualified triage unsupported. Linux completed in 28.697 seconds;
this is a fixture timing, not a capacity estimate. No LLM calls were made.

Validated image: sha256:324a6064b5d0b979b28a1f91f6be1fa7f6613d30a9f967339f465b0980372d10.
Runtime: arbitrary UID, read-only root, no network, dropped capabilities,
no-new-privileges and bounded CPU/memory/PID/tmpfs resources. Artifacts:
work/slice87-rust-macos, work/slice87-rust-linux-ubi10; initial failure retained at
work/slice87-rust-linux. Local CLI tooling checks layout, not publisher authenticity.

562 tests passed (one existing duplicate-ZIP warning), including Cargo admission,
generated metadata safeguards and durable empty-graph failure. Lint, formatting,
package build, CLI help and whitespace checks pass. No migration or user action needed.
Changes remain uncommitted.

The query does not authenticate Command ownership, prove shell execution or cover Rust
memory-safety vulnerabilities. Dependencies/macros/cfg/framework coverage and actual OCP
remain unqualified. The current language integration sequence now reaches Rust; next is
the planned C/C++ durable integration with the same minimum acceptance checks, followed
by broader query coverage and benchmark-driven improvements.
