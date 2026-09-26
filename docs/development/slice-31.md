# Slice 31: durable import pause/resume controls

Migration 0009 adds append-only import dispatch transitions. Existing imports default to
active at revision 0; migration does not rewrite their rows, runs, snapshots or reports.

```bash
uv run veriflow init
uv run veriflow import-control-status IMPORT_ID
uv run veriflow import-control IMPORT_ID paused pause-1 "Maintenance" --expected-revision 0
uv run veriflow import-control IMPORT_ID active resume-1 "Ready to continue" --expected-revision 1
```

Use the current revision returned by status for each new transition. Request keys are
idempotent within an import; repeating identical input returns the original applied
revision and current state. It does not replay an old pause after a later resume. Changed
input with an existing key, a stale revision or an already-current target state is rejected.
History is paginated in newest-first order. Reasons are operator-supplied local assertions,
not authenticated identities. Do not include secrets in them.

`worker` checks control state before recovery and before claiming each intake row.
`scan-import` checks before each selected row and reports `dispatch_status` and the next
unprocessed offset. A row whose boundary check already passed may finish after pause is
requested. No process is killed and no completed work is undone. The control command does
not acquire the worker lock, so it can record a request while capture/CodeQL runs. SQLite
contention can still fail a control request; inspect status before retrying the same key.

Resume only enables dispatch. Invoke `worker` or `scan-import` again; no daemon is started.
For scans, use the reported `next_offset` or repeat a page under the existing-attempt skip
policy. Paused imports keep their original intake/scan states. Status exposes a separate
`dispatch_control`; pause is not an analysis failure or security verdict.

Scope is import dispatch only: explicit single-run indexing/scanning, individual CodeQL
commands, triage and report retrieval remain available. This is not a global emergency
stop, cancellation mechanism, authorization boundary or distributed fenced lease. Full
run cancellation and production scheduling controls remain future work.

Tests cover migration preservation, idempotency, stale/conflicting requests, CLI resume,
capture and scan row boundaries, pagination and continued access to completed work.
