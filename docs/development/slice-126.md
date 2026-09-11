# Slice 126 — Repeatable local acceptance entrypoint

scripts/local_acceptance.py reviews retained GCS matrix evidence by default, or explicitly
runs all 18 native cases with --run-native. --tests adds the application suite. It produces
acceptance.json with passed/failed/not_run/deferred states and a consolidated matrix. Missing
reports, mismatched identities and escaping report paths fail validation. It does not claim
current-checkout acceptance from historical artifacts or turn deferred gates into success.

Validation: retained 18-case artifact audit passed; three negative tests passed for missing,
mismatched and escaping report artifacts. Ruff/diff checks pass. Fresh native dispatch and
--tests orchestration are implemented but not rerun in this slice; prior matrix/full-suite
results remain their documented baseline. No application/image/schema change or model call.

Next review and implement local PostgreSQL persistence compatibility as the first concrete
step toward the planned production database; keep SQLite as the default POC path. This is
not distributed scheduling qualification. Actual bank integrations/OCP/benchmark gates
remain deferred to authorized environments and inputs.
