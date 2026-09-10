# Slice 35: bounded retained-storage audit

`traceproof storage-audit` inventories present entries under `artifacts`, `codeql` and
`scans`. It compares recognized snapshot/attempt IDs with database records and reports
referenced, unreferenced, staging or unrecognized status. This is a review aid, not a
deletion recommendation: recovery may reuse an artifact published before a database commit.

Logical byte counts sum regular-file sizes. They are not allocated disk usage: hard links
may be counted repeatedly, sparse/compressed files differ, and database/WAL/backups and
other directories are excluded. No files are read for content or integrity verification.
Database records with missing directories are outside this present-entry inventory.

Default bounds are 1000 top-level entries and 100000 filesystem nodes; overrides are
`--max-entries` (1–10000) and `--max-nodes` (1–1000000). Directory depth is capped at 128.
Linked areas are skipped; links/special files are not followed. Errors, links or limits
produce incomplete status and explicit issues. Partial counts are observed lower bounds.
Truncated selection follows filesystem enumeration and is not a resumable sorted page.

The cooperative worker lock is held during the audit, preventing normal artifact writers
from running concurrently. A busy worker causes an error; do not remove its lock. The lock
does not prevent external filesystem mutation. This operates on trusted local state and is
not a hostile-filesystem sandbox. The lock file may be created; no artifact/database data
is modified or deleted, and no model or CodeQL calls occur.

Use `inventory_complete` only as completion of this bounded inventory, not proof that
storage is healthy or safe to delete. Inspect suspected leftovers with recovery history
before deciding retention. Automated cleanup and production retention remain future work.
Tests cover references, staging, byte counts, limits, links, empty state, locking and CLI.
No migration beyond 0009 is required.
