# Slice 122 — Packaged GCS handoff to offline scanning

Dedicated GCS acquisition Containerfile installs the optional SDK with a separate hash-locked
requirements file. Offline scanner dependencies remain unchanged. Both images contain the
same current application wheel; installed wheel/lock hashes match host build inputs.
containers/gcs-handoff-images.json records exact Linux ARM64 identities. Existing general,
C# and Rust smoke tags/inventories are preserved; the GCS scanner rehearsal uses its own tag.

A synthetic SDK boundary fixture runs in the acquisition image with networking disabled.
It exports a receipt-pinned ZIP/CSV, then a separate restricted offline container captures
and scans the source using the bounded C argv/system profile. Report projection 14 retains
GCS generation 123 and snapshot_bound provenance; one seeded candidate is exported with
incomplete coverage. No cloud calls or model calls, no claim of exploitability or recall.

Both stages use arbitrary UID, read-only root, dropped capabilities, no privilege escalation
and resource limits. The offline runtime probe passes. Build/pip checks, input hashes and
Ruff pass. No application changes, migration, image push or OCP operation. Full suite from
Slice 121 remains the application baseline (1,035 passed); native packaging checks cover this slice.

Repeat: uv build; build containers/Containerfile.gcs-acquisition as
traceproof:gcs-acquisition-linux-poc; build containers/Containerfile.ocp-smoke as
traceproof:ocp-smoke-gcs-linux-poc; run uv run python scripts/validate_gcs_handoff.py NEW_OUTPUT.
The fixture mocks SDK responses, not a real GCS service, authentication or HTTP exchange.

Next: consolidate operator intake guidance/readiness across Git, PVC and GCS, and identify
remaining functional POC gates before actual bank/OCP acceptance. This does not defer the
required real-cloud identity/network acceptance or promote untested specialized image tags.
