# Slice 112 — Durable acquisition provenance binding

Optional acquisition_receipt and acquisition_sha256 CSV columns bind a successful Git
receipt to the declared archive SHA-256 and repo_id. Receipt paths use the same scoped,
regular-file/no-symlink opener as source archives. Receipt input is capped at 1 MiB and
validated against a bounded schema. Admission stores the validated receipt in the existing
ImportItem JSON; the internal acquisition_data field is not accepted as a CSV column.
No SQL schema migration is required. Archive-only CSVs remain supported unchanged.

Snapshot processing compares every captured file path, size and SHA-256 against the admitted
receipt inventory. Mismatch fails the run without attaching a snapshot. Once admitted, the
receipt file is not reread: later removal/mutation does not replace the durable record. A
repeat submission with the same idempotency key/CSV returns the original admission; use a
new request/key for a changed receipt and its new pinned digest.

Report projection 13 includes acquisition_provenance with resolved commit, requested ref,
URL, archive/receipt hashes, Git version, file count and binding state. Before a successful
snapshot it is admitted; after content comparison succeeds it is snapshot_bound. Existing
immutable published reports remain unchanged and have no invented provenance. Publish a new
report version to reflect the new projection for an eligible run. Plain archive runs expose
null provenance; no filename-based receipt discovery occurs.

HTML/Markdown show the commit and binding status, with details in the JSON projection.
Scan/candidate CSV exports add git_commit, acquisition_archive_sha256 and
acquisition_binding_state for dashboards. Adding columns may require downstream schema updates.
No source receipt path or full file inventory is added to published summaries.

Acquisition now emits the receipt path and exact receipt digest in its generated input.csv.
The receipt itself is stored alongside it. Moving inputs to a PVC requires updating both
absolute CSV paths while preserving hashes. This is an integrity chain over operator-supplied
artifacts, not Git-server authentication, signed-commit verification, proof of repository
ownership or semantic reachability. remote_history_authenticated remains false.

Existing smoke image bases predate these optional fields and this report projection.
Do not claim this working-tree feature is already present in those pinned images. Refresh
and requalify application/toolchain image snapshots before sending provenance-enabled CSVs
to them. Ordinary archive-only smoke inputs retain their previously validated behavior.

Validation covers receipt deletion after admission, immutable exact-report retrieval,
HTML/CSV visibility, archive/repository/digest mismatch and a file-inventory mismatch that
fails snapshot processing. Native Git fixture tests and all prior archive regressions remain
in the full suite. A separate public HTTPS Hello-World acquisition/intake/report demonstration
exercises real transport and content binding, without a vulnerability scan or model calls.

Next: refresh/requalify container application snapshots for the current intake/provenance
contract. Git-URL CSV dispatch, private gateway/CA/credentials, GCS, bank benchmark and actual
OCP qualification remain open. No migration, deployment or model key was needed here.

Final validation: 1,003 tests pass with one existing duplicate-ZIP fixture warning. Ruff,
formatting, whitespace and package build checks pass. Public acquisition artifacts are
work/slice112-git and work/slice112-state. The example report is intake-only, not a scan
result; it binds commit 7fd1a60b01f91b314f59955a4e4d4e80d8edf11d to captured content.
