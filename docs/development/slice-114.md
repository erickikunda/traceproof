# Slice 114 — Bounded repositories.csv acquisition

Added acquire-git-csv, a sequential networked acquisition step reusing the existing HTTPS
allowlist, revision resolution, source limits and receipt emitter. Exactly five CSV fields
are supported: repo_id,url,revision,owner,classification. One MiB input and 1–10 records are
validated before work; per-row validation failures remain visible without blocking later
valid rows. The input CSV is read once and its digest recorded. There is no filename watcher.

Successes emit one combined archives.csv with receipt/archive pins and separate row output
directories. acquisition-batch.json records every input row including failures and undispatched
work. Batch acquisition timeout is bounded, rows inherit at most 300 seconds, and repeated
output directories are rejected. Partial success exits nonzero. Downstream scanning of the
success subset must retain the original summary; it does not erase acquisition failures.
No database migration, scans, model calls or automatic retries.

Unit tests exercise real local Git export followed by durable receipt-bound archive intake,
continuation after a credential-bearing URL rejection, CLI success/failure, zero-success CSV
absence, whole-batch size rejection, deadline states and infrastructure interruption. The
public HTTPS demonstration uses two Hello-World rows with an unapproved host between them;
it must acquire/snapshot the valid rows, reject the middle row and exit incomplete.

The batch JSON and CSV are separate atomically replaced files, not one durable transaction;
consumers must await terminal success/incomplete status. This is not resumable/distributed
or a fleet throughput claim. Existing public-only Git, content and network limits persist.
Per-row output may accumulate; temporary-work monitoring is not a filesystem quota.

Next: package the networked acquisition stage separately from offline scanner images, with
explicit input/output handoff and bounded local rehearsal. Private bank credential/CA/proxy,
GCS, representative benchmark, production persistence and actual OCP gates remain open.

Final validation: 1,009 tests pass with one existing duplicate-ZIP fixture warning. Lint,
formatting, whitespace and package build checks pass. Real public-HTTPS artifacts are
work/slice114-public-batch; both successful rows snapshot with their pinned receipts in
work/slice114-state. The middle unapproved-host row fails without network acquisition;
the CLI correctly exits 1. Zero scans and model calls.
