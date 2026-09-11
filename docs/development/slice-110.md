# Slice 110 — PVC archive manifest convention in the smoke workflow

The common offline entrypoint selects exactly one archives.csv or legacy input.csv.
It rejects both names together, missing input, repositories.csv, symlinks and non-files.
No filename guessing or Git network dispatch is introduced. The selected basename is
recorded in result.json and the same path is handed to existing CSV admission. Existing
read-only mount requirements apply; operators must finish staging before invoking work.

The rehearsal runner defaults to archives.csv and provides --manifest-name input.csv for
legacy validation. Shared entrypoint tests cover success/failed-analysis export with both
names and pre-scan rejection of ambiguous/invalid source shapes. The general, C# and Rust
smoke layers are rebuilt; their underlying pinned application/toolchain snapshots remain
unchanged. No schema migration, provider calls, registry push or cluster apply.

The narrow smoke Job still accepts one row. General multi-row CLI archive intake remains
available. Next implement bounded mounted multi-row batch handoff using that existing
intake/scan machinery, without requiring Git or credentials. Durable Git provenance remains
planned after this user-requested mounted-intake integration. Actual OCP remains deferred.

Validation: 994 tests pass (one existing duplicate-ZIP fixture warning). Eight restricted
Docker scans pass: C vulnerable/fixed for archives.csv and input.csv, plus C#/Rust pairs
using archives.csv. Exact JSON/HTML exports and selected manifest attribution pass; zero
model calls. Lint, formatting and whitespace checks pass. No actual OCP execution.

- c, archives.csv: sha256:5ad963f2df9284fd20d61fb3ef684c0fa15bad9bb2c75ff0e66dd8677a00632f
- c, input.csv: sha256:5ad963f2df9284fd20d61fb3ef684c0fa15bad9bb2c75ff0e66dd8677a00632f
- csharp, archives.csv: sha256:7754d296d8814b31c6da938e095c1195560309bdcf1a176a18bcb60db8c20d86
- rust, archives.csv: sha256:b51c66613a1da5173060b8c0a1fd85be7b85ef80b75e8ee805629c0a7ff51b4c
