# Slice 106 — Offline OCP smoke bundle and local rehearsal

Implemented a digest-pinned smoke image layer, namespace manifest renderer/example and
one-archive C argv-to-system entrypoint. It uses the shared intake/scan/exact report APIs,
disposable SQLite and no model adapters. Reports go to a separate export mount, input is
read-only and scratch is explicit. Unique execution directories prevent export overwrite.
Failures return nonzero and preserve available reports plus bounded log prefixes.

The Job disables token automount, grants no API roles, drops capabilities, denies privilege
escalation, uses read-only root and RuntimeDefault seccomp, declares resource/deadline limits
and selects ARM64. UID/group assignment is left to OCP admission. The selected-pod policy
denies ingress/egress, subject to additive policy and actual cluster enforcement checks.
No namespace/PVC is created by the renderer. No cluster apply or registry push occurred.

Local restricted Docker acceptance passes both vulnerable/fixed archives with 1/0 candidates,
exact JSON/HTML reports and zero model calls. Image digest:
sha256:9bda91db610a74bc64e497ca0549900892f50038b446b06e23b0e167389861f6.
Artifacts: work/slice106-ocp-smoke-final. The initial rehearsal failed because scratch was
not executable; aligning it with the previously qualified Joern mount settings restored
execution. Failed-analysis export/exit semantics have a regression test.

This is a narrow C-profile OCP-2 subset. No OCP admission, server schema check, SELinux/PVC
validation, AMD64 support, distributed durability or bank throughput has been qualified.
OOM/deadline termination may prevent final exports. The image retains the tested Slice 104
base wheel; new application changes require rebuilding/requalifying that base. No migration.

See [deployment/operator instructions](../guides/traceproof-ocp-smoke-guide.md). Next representative
mounted-input integration across supported profiles, before wider CLI refinement; actual
bank OCP, live gateway, ground-truth and fleet acceptance remain open.

Validation: 956 tests pass, with one existing duplicate-ZIP fixture warning. Ruff,
formatting and whitespace checks pass. Nine new tests cover configuration restrictions,
invalid inputs, export overwrite prevention and failed-analysis exit semantics.
