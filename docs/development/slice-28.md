# Slice 28: explicit CodeQL resource tuning

`codeql-extract`, `codeql-analyze`, `scan-run` and `scan-import` now accept
`--threads` (1–64, default 2) and `--ram-mb` (2048–262144, default 2048).
The Python operations validate strict integers before source access or attempt creation.
Zero/negative automatic core selection is deliberately excluded so requests stay explicit.
These are application policy bounds, not a statement about available machine capacity.

```bash
uv run veriflow scan-run RUN_ID /absolute/approved.ql --threads 1 --ram-mb 4096
uv run veriflow scan-import IMPORT_ID /absolute/approved.ql --limit 5 --threads 2 --ram-mb 4096
```

Pipeline commands use the same settings for extraction and query execution. Individual
stage commands can use different settings. Each new extraction and query attempt records
`requested_resources` with `threads` and `ram_mb`, including unsuccessful attempts.
Query attempts also record their timeout. Retrieve these through `codeql-status` and
`scan-report`; older attempts do not acquire inferred settings. Immutable published
summary reports are unchanged; their attempt IDs link to the detailed records.

Settings are passed as separate CodeQL argv entries. The installed CodeQL 2.27.0 help
was checked: create treats these as import/build hints; analyze treats RAM as an evaluator
target, may exceed it with file-backed mappings, and rounds values below 2048 MB upward.
These controls are not OS CPU/memory enforcement, total process-tree RSS limits, disk
quotas, container requests or Kubernetes limits. Leave capacity for Python, CodeQL/JVM
overhead and the OS. OpenShift resource configuration and load qualification remain open.

Changing settings does not override `scan-import`'s existing-attempt skip policy; use
explicit `--rescan` when another attempt is intended. No new concurrency, retries, caches
or model calls are introduced. Defaults preserve prior behavior. No migration is needed.

Tests verify invalid values fail before storage, exact subprocess flags, durable records,
CLI pipeline forwarding and batch forwarding. Synthetic process results are used; this
slice does not claim performance gains or 1000-repository/day capacity measurements.
