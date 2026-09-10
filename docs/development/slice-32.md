# Slice 32: terminal import dispatch cancellation

```bash
uv run traceproof import-control-status IMPORT_ID
uv run traceproof import-control IMPORT_ID cancelled cancel-1 "No longer needed" --expected-revision 0
```

Use the current revision, which may differ from the example. `cancelled` is a terminal
dispatch state: active or paused imports may transition to it; new transitions after
cancellation are rejected. Repeating the same key and identical request returns its
recorded revision. Replaying an earlier pause/resume key returns the historical applied
revision plus current cancelled state; it cannot change that state.

Intake and batch scans stop at the next row boundary, just as for pause. A row whose check
already passed may finish and publish its result. Cancellation does not erase or rewrite
intake rows, attempts, snapshots, reports, evidence, triage records or budgets. Existing
reports remain retrievable. Unstarted intake rows retain their state and attempt count;
the separate dispatch control explains why they are no longer being scheduled.

`scan-import` returns `dispatch_status: cancelled` and no continuation offset once it
observes cancellation. Returned rows show work already visited; compare their count with
the selected count to identify undispatched work. Reinvocation, including `--rescan`,
does not bypass the cancelled import. To schedule a new import, explicitly submit with a
new intake idempotency key. There is no automatic replacement import or refund.

This is cancellation of import dispatch, not termination of the underlying runs. Explicit
single-run tools and triage remain available. It is not an emergency process stop or an
authorization barrier. Process termination, distributed cancellation and broader run
lifecycle contracts remain future work. M1.6 remains partial.

The existing 0009 audit table supports this additional state; no migration is required.
Do not run an older application version against a state directory containing cancellations.
Tests cover active/paused cancellation, replay of old keys, terminal transitions, CLI,
capture/scan boundaries, retained rows, empty-page status and rescan behavior.
