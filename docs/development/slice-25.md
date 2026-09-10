# Slice 25: bounded sequential import scanning

After CSV admission and archive capture:

```bash
uv run traceproof scan-import IMPORT_ID /absolute/approved.ql --limit 5
uv run traceproof scan-import IMPORT_ID /absolute/approved.ql --offset 5 --limit 5
```

This selects rows in original CSV order and invokes the existing source-only `scan-run`
operation sequentially. Default limit is 1, maximum 1000. The result contains every selected
row's intake state and scan outcome, aggregate counts and `next_offset`. Rejected or
uncaptured rows are skipped explicitly and still consume a page position. Run `worker`
first to capture admitted archives. No source capture, model calls or query downloads are
triggered by this command.

Existing query attempts of any status are skipped by default, under the same worker lock
used to start analysis. Failed/interrupted attempts are not automatically retried or
treated as successful. `--rescan` explicitly starts fresh extraction/query work. Runs
blocked before a query attempt exists may be retried on another invocation. An existing
attempt without a report is not republished automatically; use its ID with `publish-report`.

Expected row-level application errors are returned and later rows continue. Infrastructure
errors stop the command; completed per-run artifacts remain durable. The batch summary
itself is not persisted: redirect JSON if needed. Following interruption, inspect run/scan
history before repeating a page. The batch does not hold a lock between complete runs,
has no background execution or atomic portfolio snapshot, and is not a distributed
scheduler or 1000-repositories/day qualification.

`--extraction-timeout` and `--query-timeout` retain stage-level limits. Mixed outcomes
can exit zero; inspect row statuses and counts. A skipped row or zero candidates is not
a clean security verdict. No migration beyond 0008 is needed.

Tests cover mixed/rejected/uncaptured rows, error continuation, pagination, CLI output,
explicit rescan forwarding and skipping existing attempts before indexing/tools.
