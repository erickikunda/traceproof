# Slice 107 — Mounted smoke workflow across seven language selections

The offline smoke entrypoint and namespace renderer now accept an explicit language, with
one shared packaged language/profile allowlist. Java, Python, JavaScript, TypeScript, Go,
C and C++ select their existing bounded discovery profiles. C remains the default. The
result record includes the chosen language/profile; exact report exports and per-execution
failure/overwrite behavior are retained. No migration or application-wheel change.

This image still uses the pinned Slice 104 Joern/grammar base. C# and Rust fail selection
before scan state because their repaired frontend / Rust toolchain require separate images.
Auto and mixed-language orchestration are not added. No live or replay model is invoked.
This is deployment integration, not additional query/framework coverage or enterprise-repo
qualification. Tiny synthetic fixture archives do not substitute for representative bank data.

The rehearsal runner now accepts each selection and verifies vulnerable/fixed mounted ZIP
inputs, language/profile attribution, exact JSON/HTML report identity and incomplete review
readiness. Configuration/dispatch tests check every selection, source-registry agreement,
no advisory injection and early rejection of unsupported toolchains. Java's default profile
must be passed as None to the scanner; an initial native run caught the string-default
mismatch and that mapping is regression-tested.

Local image digest:
sha256:9dd9ae9b823ff183a2201628e9c6a6630232dbc37ac050642790addd71c35614.
Final run artifacts: work/slice107-final-<language>. All seven selections pass their
vulnerable/fixed mounted-input pair: 14 native scans, 1/0 candidates per pair, zero model
calls. The full suite passes 967 tests (one existing duplicate-ZIP fixture warning);
the updated smoke tests pass independently after the Java default fix. Lint, format
and whitespace checks pass. Restricted Docker remains local preparation only:
ocp_qualified=false. No cluster apply, image push, provider call or migration occurred.

Next: apply this same bounded mounted-input contract to the qualified C# repair and Rust
images, keeping tooling identities and restrictions explicit. Ground-truth, real-repository,
actual OCP and fleet acceptance remain separate open work.
