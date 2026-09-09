# ADR 0001 — Deliver local intake before analysis

Status: accepted for the personal POC, 9 September 2026.

The first logical slice implements the foundation and local intake parts of M0/M1.
It creates an immutable source snapshot from an admitted CSV row, persists progress,
and exposes status through a CLI. It does not attempt all of M0–M2 in one change.

Use Python 3.12, Pydantic contracts, SQLAlchemy with Alembic migrations, Typer and a local
filesystem artifact adapter. Use a single OS-locked worker with per-item transaction
boundaries. Actual process death releases the lock; a new owner recovers in-progress
rows. Do not use wall-clock age to strip healthy ownership. PostgreSQL fencing/heartbeats
belong to the distributed implementation and remain explicitly deferred.

Unpack TAR/TAR.GZ/ZIP using controlled streams and our own writes, not `extractall`.
Reject links and special members, confine archive input with descriptor-relative opens,
bound resources and write staged artifacts before publishing their manifest and DB
reference. The immutable snapshot ID includes repository, classification and archive
digest. This intentionally avoids sharing artifacts between repository identities.

CSV admission and artifact processing are separate durable steps. An optional expected
digest binds the requested source bytes; otherwise source identity becomes immutable
only after capture. Idempotency is request-based and never hides changes behind a reused
key. Invalid rows do not prevent valid rows from progressing.

No `complete` scan state exists in this slice. `snapshotted` is a checkpoint. Status
explicitly says analysis was not performed and no scan report is available.

Consequences: useful intake and failure tests can run without models or CodeQL; Git/GCS,
additional CSV metadata, scan/evidence/report contracts and a real analysis stage follow
later. Local filesystem permissions do not constitute the enterprise execution sandbox.

References consulted for transaction and archive behavior:

- [SQLAlchemy SQLite transactions](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [Python archive extraction guidance](https://docs.python.org/3/library/tarfile.html#extraction-filters)
