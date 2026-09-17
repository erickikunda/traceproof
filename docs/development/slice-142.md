# Slice 142 — Snapshot file inventory export

Added `get-sbom`, a deterministic CycloneDX 1.6 export of a snapshot's recorded manifest.
Each manifest entry becomes one `file` component carrying its SHA-256 and size; the root
component carries the repository identifier, snapshot identity and archive digest. The
document omits a publication timestamp and derives its serial number from the snapshot
identity, so an unchanged snapshot always exports identical bytes.

`sbom_export.py` follows `sarif_export.py`: repository ownership is checked before any
manifest is read, and the component count (20,000) and encoded size (8 MiB) bounds refuse
rather than emit a truncated document. `--verify` re-reads and re-hashes the stored tree
through `ArtifactStore.verify` and compares it to the admitted database record, recording
`recorded` or `reverified` in the document. The export is deliberately not part of
`render_report`: the published report body is capped at 8 MiB and is keyed to a run and
attempt, not a snapshot.

Eleven new tests cover document shape, hash and size agreement with the recorded manifest,
determinism, absence of any package or vulnerability claim, opt-in reverification, detection of a
modified tree under `--verify`, cross-repository refusal, unknown snapshots, both bounds, and an
invalid manifest record. The changed files pass lint and formatting against an unchanged repository-
wide baseline, and the full suite passes: 1,072 tests. No migration, no schema change, no projection
change.

**This is a file inventory, not a dependency bill of materials.** No dependency manifest or
lockfile of a scanned repository is parsed anywhere in the codebase, so the document carries
no package identities, no Package URLs, no resolved transitive dependencies and no license
inventory. The `vulnerabilities` array is absent by construction; no vulnerability position
is established. It is not a supply-chain attestation and is unsigned. It is unrelated to the
container image SBOM discussed in the implementation plan, which describes TraceProof itself.

Next: tier 2 of the [SBOM and OSV export roadmap](../plans/sbom-osv-export.md) — a bounded
dependency discovery stage emitting candidate components with explicit pinned/unpinned
provenance and a `dependency_coverage` gap record. OSV matching remains behind tier 2 and
needs a pinned database acquired by the networked acquisition container.
