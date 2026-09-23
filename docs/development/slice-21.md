# Slice 21: one-command source-only scan

```bash
uv run veriflow scan-run RUN_ID /absolute/approved.ql --extraction-timeout 300 --query-timeout 600
```

For an already captured run, this command validates the operator query entry, builds or
reuses its Python index, gates on readiness, extracts a fresh CodeQL database, executes
the selected local query/suite and publishes the exact new query attempt. It returns a
compact JSON stage summary with extraction, query-attempt and report IDs. No model calls,
query downloads or source builds are added.

Blocked indexing or unsuccessful extraction stops progression, with `report_id: null`.
It never repackages an older scan as the result of a failed new extraction. Inspect
`repo-report` or `codeql-status` for details. Once a query attempt exists, its stored
failure/partial outcome is published as an incomplete report. Static review readiness
does not mean security completeness. Durable blocked/incomplete results can exit zero;
automation must inspect returned status, not just process exit.

Indexing/extraction/queries run under the existing local worker lock. Publication takes
its own lock and uses exact run/attempt IDs even if another operation starts between
stages. A publication error leaves the query attempt available; use `scan-history` and
`publish-report --run-id ... --attempt-id ...` to publish it explicitly.

Repeated invocation is an explicit fresh extraction/query request, not an idempotent
resumption or cache hit. Index checkpoints may be reused. On interruption inspect
existing stage results before rerunning. Timeouts apply per CodeQL stage, not to the
whole workflow. This command is not a background scheduler, bulk runner or throughput
qualification. Archive admission/capture and advisory triage remain separate commands.

No schema migration is needed beyond 0007. Tests cover blocked index, extraction failure
with existing history, exact-attempt publication, CLI options and query/timeout preflight.
Real synthetic CodeQL verification covers vulnerable, fixed and incomplete cases.
