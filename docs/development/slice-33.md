# Slice 33: import history and dispatch-state discovery

```bash
uv run veriflow import-history --limit 20
uv run veriflow import-history --state paused --limit 20
uv run veriflow import-history --state cancelled --offset 20 --limit 20
```

Returns newest imports first, with ID as a deterministic timestamp tie-breaker. Optional
state filters are active, paused or cancelled and apply before pagination. Default page
size is 100, maximum 1000. `total` counts matching imports; `next_offset` is null at the end.
An initialized empty database returns an empty history. Each page uses one read transaction;
new admissions and control changes may shift later pages.

Each row includes import ID, admission timestamp, request digest, latest dispatch state
and revision, total intake rows and counts by intake state. Imports without control history
are active at revision 0. Counts cover all rows in that import; multiple control transitions
do not duplicate counts. These are intake counts, not scan success or vulnerability counts.
An active import can have no remaining intake work; a cancelled import can retain ready rows.

Use the ID with `status`, `import-control-status`, `import-reports`, `worker` or `scan-import`
as appropriate. History itself performs no capture, scanning, publication or model calls.
Its projection excludes source URIs, input roots, request keys, error prose and control
reasons. The local OS account remains the access boundary; this is not a tenant-filtered API.

Tests cover default state, latest-transition selection, state filters, tie ordering,
pagination, row-count reconciliation, empty histories, invalid input, CLI and projection
privacy. No migration beyond 0009 is required. Fleet performance is not qualified.
