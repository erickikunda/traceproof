# Slice 70 — Rust initial Joern feasibility passed

Assessed Joern 4.0.625 macOS ARM64 using four dependency-free Rust Cargo fixtures.
The initial loose .rs input failed preparation with 'no projects' and still left a graph
artifact; artifact existence and exit status alone must not qualify Rust preparation.

Installed the official Rust 1.98.1 toolchain and matching rust-src under ignored
`work/rust-toolchain/local`, verifying both archive SHA-256 values against the official
release manifest. Pins are recorded in `scripts/joern/rust-toolchain.json`. No system PATH
or global Rust configuration was changed. Probe subprocesses prepend this local toolchain,
set Cargo offline mode and operate on copied fixtures. No external crate dependencies,
custom build scripts or application execution are involved.

| Fixture | Sources | Argument sinks | Flows |
|---|---:|---:|---:|
| Single-file vulnerable | 1 | 2 | 1 |
| Single-file fixed | 1 | 2 | 0 |
| Three-file vulnerable | 1 | 2 | 1 |
| Three-file fixed | 1 | 2 | 0 |

The cross-file path retains six nodes across main, service and repository modules. All
returned code fragments matched their reported source lines in this sample; original
source hashes were unchanged. These checks do not establish general Rust source mapping.
Raw results/logs/graphs: `work/slice70-rust-crossfile`; early preparation diagnostics are
under `work/slice70-rust`. Repeatable runner: `scripts/validate_joern_rust.py`.

The query selects lookup(input) and arg calls by name. It proves fixture-level data-flow
feasibility, not web-framework modeling, command ownership, unsafe-memory detection or a
complete command-injection rule. The fixed fixture replaces shell input with a constant;
it is not a broad sanitizer test. No Rust backend or qualified triage is enabled.

Remaining gates: dependency/macro/cfg handling, prevention of untrusted build-script and
procedural-macro execution, fully pinned preparation inputs, Linux/OCP runtime behavior,
larger projects, meaningful CWE coverage and false-positive qualification. Cargo offline
mode is not OS network isolation. A Cargo-aware preparation profile will be needed; the
Java-only source-copy policy cannot be reused unchanged.

Validation: four real probe cases passed. Existing 521 tests, lint/format, whitespace and
package build checks pass. No migration, bank data or LLM call. No user action is needed.

Next: Python, JavaScript/TypeScript, Go and early C/C++ feasibility. As requested, defer
C# remediation and final backend decisions until these assessments are complete.
