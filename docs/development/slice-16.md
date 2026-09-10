# Slice 16: repository run and query-attempt history

Operators can discover work before a report is published:

```bash
uv run traceproof run-history REPO_ID --limit 100
uv run traceproof scan-history REPO_ID --limit 100
uv run traceproof scan-history REPO_ID --run-id RUN_ID --offset 0 --limit 100
```

Run history includes admitted/failed runs, their snapshot and latest query-attempt ID.
Scan history includes all stored query attempts, including failed or unpublished attempts,
with status, execution completeness and candidate count. It does not list CodeQL database
extraction attempts; retain their IDs for `codeql-status`. Absent counts/completion values
stay null. A run without a query attempt has an empty scan history.

Both responses include total, offset, limit and next_offset (null on the last page).
The default limit is 100 and maximum 1000. Runs sort by admission time descending, with
ID tie-breakers. Scans group by that run order, then attempt time/ID descending. Ordering
does not depend on publication. Each page uses one read transaction; new admissions can
shift offset pagination across requests. This is a local browsing interface, not a frozen
portfolio export. No PostgreSQL/fleet performance claim is made.

Missing repositories and runs belonging elsewhere fail explicitly. Known empty histories
return empty lists. Summaries omit raw diagnostics, source locations and model/review prose.
Use exact run/attempt IDs with existing status/report commands for detail. These reads
do not publish artifacts or trigger source, CodeQL or model activity.

Validation covers unpublished/failed work, null versus zero counts, repository isolation,
empty pages, page limits, CLI JSON and absence of database writes. Schema remains 0006;
no migration is required. The operator guide now explains these discovery commands.
This advances the M2 historical scan-listing surface without claiming full M2 acceptance.
