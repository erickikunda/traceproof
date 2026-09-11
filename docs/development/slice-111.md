# Slice 111 — Bounded mounted archive batch execution

Added a separate ocp_archive_batch.py entrypoint to the general and specialized smoke images.
It reuses archive manifest selection, existing CSV admission/snapshotting and scan-import
pages of one. The renderer opts in with --batch-max-rows 1–10; it adjusts the bounded Job
deadline while preserving security/storage settings. Default one-row smoke behavior remains.
One selected language/profile applies to every row, with existing C#/Rust tool identity gates.

Every input record gets an explicit state in batch.json. Valid rows export exact JSON/HTML
reports into row-numbered directories. Invalid intake rows do not prevent later valid scans.
A batch with any unexported row exits nonzero and retains successful results. Infrastructure
exceptions stop execution with remaining row states visible. Summaries use atomic replacement
but are not fsync/restart guarantees. SIGKILL/OOM can leave a running summary; Job state matters.

Limits: at most ten CSV records, one sequential worker, 180-second prepare/query stage limits,
and the image/Job's existing scratch/resource limits. All-row success means partial discovery
reports exported, not complete security or clean repositories. No provider calls, Git retrieval,
shared SQLite, migrations, automatic retry or actual OCP execution is introduced.

Unit tests cover continuation after intake rejection, pending state after infrastructure
failure, whole-manifest row-limit rejection and rendered batch entrypoint/deadline. Native
rehearsals use both valid and missing-archive batches on C, C# and Rust images, exercising
all three toolchain variants. Other general-image languages retain their prior qualification;
this slice does not claim a new per-language batch native run for each of those selections.

See deployment README for run commands, export structure and limitations. Next return to
durable Git acquisition provenance in intake/reports. Private credentials, GCS, representative
bank benchmark, shared persistence and actual OCP admission remain open acceptance work.

Validation: 998 tests pass (one existing duplicate-ZIP fixture warning); lint, format and
whitespace checks pass. Six native batch scenarios pass across C/C#/Rust: twelve scans
plus three missing-archive rows. All-valid batches exit 0; mixed batches exit 1 while
exporting both valid reports (1/0 candidates). Zero model calls. Artifacts and images:
- work/slice111-batch-c: sha256:7787fb2f91c1312a65cf6a643ae260d1b2070e2776ec645efe5cd2378acefcc3
- work/slice111-batch-csharp: sha256:f9223d927b0ef1ec684eaccf20b5dad47139a9ccf717f771542c04279000b87b
- work/slice111-batch-rust: sha256:fc81add40bb6c3c9398e6056808dfa77feaf51d350b21f240e6e8e8f47c74d61
