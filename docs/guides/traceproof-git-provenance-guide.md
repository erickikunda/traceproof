# Persisting Git acquisition provenance


New acquire-git output includes acquisition_receipt and acquisition_sha256 in input.csv,
alongside the archive sha256. Admission validates and copies the receipt into durable state;
worker compares its file inventory against the captured snapshot. Keep the source archive
available until snapshotting; the receipt file is no longer needed after successful admission.

If moving to a PVC, update source_uri and acquisition_receipt to container-visible absolute
paths beneath input-root. Preserve both digest values. Archive-only archives.csv batches
need neither receipt column. Receipts are explicitly opted in, never discovered by filename.

A successful source snapshot adds acquisition_provenance.state=snapshot_bound to newly
published report projection 13, with resolved_commit and archive/receipt digests. This is
operator-supplied content binding; remote_history_authenticated remains false. Earlier
published reports stay immutable. HTML/Markdown display the commit and CSV exports add
Git commit/archive digest/binding-state columns. Existing dashboard consumers should allow
those additional columns.

An existing idempotency key returns its original admitted receipt even if the external file
has since changed. To admit a replacement, supply its updated SHA-256 and a new request key.
Digest/repository/archive mismatches reject admission; file inventory mismatch fails capture.
A failed or absent snapshot is never labeled snapshot_bound.

Pinned OCP smoke image bases currently predate this feature. Use the current local checkout
for provenance-enabled intake until updated container snapshots have been rebuilt and
qualified. Do not strip receipt hashes to pretend provenance survived an older image.
