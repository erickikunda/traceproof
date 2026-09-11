# Rust feasibility probe

Pinned local setup: Joern 4.0.625 macOS ARM64 and Rust 1.98.1 with Cargo, the matching
standard library and rust-src. Official Rust archive pins are in rust-toolchain.json.
The local installation is under ignored work/rust-toolchain/local; system PATH is unchanged.
For reproducible setup, verify archives against their SHA-256 values and install with
an explicit project-local prefix. rust-src enables standard-library loading.

```sh
uv run python scripts/validate_joern_rust.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --rust-home work/rust-toolchain/local \
  --output work/joern-rust-new
```

Use a new output directory. The runner copies the dependency-free Cargo fixtures into
scratch, sets Cargo offline mode and preserves original file hashes. Generated Cargo
artifacts remain in scratch. Cargo offline mode is not OS network isolation and is not
an assurance that arbitrary build scripts or procedural macros cannot execute. These
fixtures contain no custom build scripts or external dependencies. Untrusted enterprise
Cargo intake needs separately enforced runtime/build policy before deployment.

The query deliberately selects lookup(input) and arg call arguments. It does not model
web request sources, prove Command ownership, or distinguish every safe use of argv.
The examples use sh -c only to test an explicit source-to-shell-argument flow; they are
never executed. Single-file and three-file module variants have vulnerable/fixed pairs.
Report nodes retain file hashes and line/code comparison results; these observations are
not general source-map qualification. Parse logs must be inspected even if extraction
exits zero or leaves a graph artifact.

The raw .rs-only attempt failed with 'no projects'. A Cargo manifest and toolchain were
needed in this configuration. A graph file alone is insufficient evidence of successful
preparation. This is a language feasibility test, not an enabled Rust TraceProof backend,
CWE coverage guarantee, restricted Linux test or bank OCP qualification.
