# Slice 34: CodeQL extraction-attempt discovery

```bash
uv run veriflow extraction-history REPO_ID --limit 20
uv run veriflow extraction-history REPO_ID --run-id RUN_ID
uv run veriflow codeql-status EXTRACTION_ATTEMPT_ID
```

This read-only history complements query `scan-history`. It includes stored extraction
attempts even when they failed before analysis, with exact IDs, run IDs, recorded status,
elapsed/timeout seconds, CodeQL version, baseline setting and requested thread/RAM values.
It does not include database paths or raw logs. A recorded running state is not a liveness
probe, and successful extraction is not a completed security scan.

New extraction attempts record their creation time in their existing JSON result. Legacy
attempts retain null timestamps; nothing is backfilled or inferred. Ordering groups newest
admitted runs first, then dated attempts newest-first within each run, followed by undated
attempts ordered by descending ID. IDs break timestamp ties and do not imply chronology
for undated records. The timestamp is attempt creation time, not completion time.

Default page size is 100, maximum 1000. Optional run filtering enforces repository scope.
Responses include total, offset and next_offset; an empty known repository has no attempts.
Each page reads one transaction, while new work may shift subsequent offset pages.
No extraction, scan, model call, recovery or publication is triggered by retrieval.

Use the exact ID with `codeql-status` for full diagnostics or explicitly with
`codeql-analyze` if extraction succeeded and a query run is intended. History does not
automatically select/retry an attempt. Stored success does not verify that retained
database files still exist. No migration beyond 0009 is needed.

Tests cover dated/undated ordering, scope, pagination, empty history, CLI, omission of
artifact paths and timestamp persistence. Production indexing and fleet performance
qualification remain future work.
