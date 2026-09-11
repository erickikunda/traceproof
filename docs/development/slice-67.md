# Slice 67 — Restricted Linux Joern runtime

Added `containers/Containerfile.joern` and a separate `traceproof:joern-linux-poc` image.
It uses digest-pinned UBI 9 Python 3.12, the locked TraceProof wheel dependencies, Joern
4.0.625 Linux ARM64 and Temurin 21.0.12.1+1. Both tool archives are checked during build;
pins are recorded in `containers/joern-toolchain.json`. No CodeQL or .NET tooling is
included in this runtime. Download/build networking is separate from scan execution.

The existing container validator now supports `--suite joern`. Seven synthetic cases
exercise archive intake, durable Joern attempts, candidate retrieval, published reports,
coverage accounting and unqualified Joern evidence bundles. The packaged acceptance
runner exports HTML/JSON plus failure logs; it does not invoke an LLM.

Execution restrictions:
- Linux ARM64, UID 1000710000 / GID 0;
- read-only root, network none, all capabilities dropped, no-new-privileges;
- 2 CPU quota, 4 GiB container memory, 256 PIDs;
- bounded writable work/tmp tmpfs and a report-only host bind mount;
- no Docker socket or Kubernetes service-account token.

The runtime probe checks the effective identity/security state, denies root writes and
external network connections, and verifies writable scratch/report paths. Image ID,
Docker configuration/state, Java/Python/OS inventories and stage logs are retained.
Application reports do not themselves attest to the enclosing container policy; consult
runtime.json and container-config.json for the independent harness evidence.

This is local restricted Linux acceptance, not OCP qualification. Bank SCC admission,
SELinux/PVC behavior, network policy, registry mirroring, quotas and shared storage remain
for the authorized OCP dev environment, deferred until functional POC completion.
No local OpenShift installation is needed. ARM64 success does not qualify x86_64 binaries.
Parser diagnostics, broad framework coverage and fleet throughput remain unqualified.

Validation: 518 tests pass (one existing duplicate-ZIP fixture warning), Ruff lint/format
and diff whitespace checks pass; the image builds with verified archive hashes.
Real runtime and fixture results are retained under `work/slice67-joern-linux`.
No migration or bank data was needed.

Next: qualify Joern parser diagnostics and move to the early C#/Rust language gates.
C/C++ full support remains after the current language work plan.

Real acceptance passed all seven cases in 50.322 seconds: vulnerable/renamed each yielded
one candidate; fixed/disconnected/annotation-lookalike/sink-lookalike/unmapped-route
returned zero. All reports remain incomplete/discovery-only. Runtime probe passed;
container exited zero without OOM. This tiny-fixture timing is not a fleet capacity claim.

Validated immutable image:
`sha256:75122bbf456fb6afb3bbd4d7e995835c005d05717e94b964653423b90eff09ba`.
