# Slice 121 — Durable GCS archive provenance

GCS acquisition now emits repo-bound, digest-pinned receipt columns in archives.csv.
Intake validates and persists the typed GCS receipt alongside the existing Git contract.
After archive capture, receipt size and SHA-256 must match the captured archive manifest.
No remote read occurs during admission, capture or report retrieval.

Report projection 14 adds cloud source fields to shared CSV projections and renders
bucket/object/generation in HTML/Markdown. Exact historical reports retain their prior
projection version. Git receipt file-inventory verification remains unchanged. GCS binding
is to archive bytes, not a separately supplied extracted-file inventory, and does not
independently authenticate remote cloud history. Plain archives still have no provenance.

Four new tests cover durable retrieval after receipt deletion, all readable/tabular formats,
receipt hash/repository rejection and archive-size mismatch after capture. Targeted GCS/Git
provenance suite: 17 passed. Full suite: 1,035 passed with one existing duplicate-ZIP warning (work/slice121-tests.log).
No SQL migration, cloud access, live model calls or image rebuild. Next refresh acquisition
packaging with the optional GCS SDK and qualify the offline report handoff locally.
