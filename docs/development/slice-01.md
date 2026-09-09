# Slice 01 — local intake and snapshot foundation

## Scope

Implemented: pinned project environment, versioned intake/file/snapshot contracts,
SQLite schema migration, CSV admission with per-row results, local TAR/TAR.GZ/ZIP
capture, source scope enforcement, resource bounds, integrity verification, durable
status, request idempotency and local interrupted-work recovery.

Milestone coverage: a bounded subset of M0 and M1. The complete M0 evidence/report and
benchmark contracts, Git intake, PostgreSQL verification and M2 analysis/report pipeline
remain open. No milestone is marked fully achieved solely by this slice.

## Environment observed

- Host architecture: Apple ARM64.
- Installed development interpreter: CPython 3.12.13; `.python-version` selects 3.12.
- CodeQL CLI: 2.26.3; Python extractor discoverable through `codeql resolve languages`.
- Approximately 435 GiB available on the repository volume at setup.
- RAM probe was blocked by the tool environment; not assumed for sizing.

CodeQL executable/extractor discovery is not proof of a complete analysis. A small
database-creation smoke check is recorded separately when performed. Production
throughput has not been measured.

## Validation

The test suite covers mixed-validity imports, idempotency conflict, source/digest
pinning, TAR/ZIP defenses, corrupt/oversized archives, file-inventory integrity,
single-worker ownership, interrupted state recovery, repeat migrations and CLI flows.
Results from this implementation session:

- `pytest`: **53 passed**. The one warning comes from deliberately constructing a
  duplicate-path ZIP fixture; the resulting archive is correctly rejected.
- `ruff check .` and `ruff format --check .`: passed.
- `uv build`: source distribution and wheel built, including the migration package.
- CLI demo: CSV admitted, two files snapshotted, all digests verified, and status
  explicitly reported `analysis_performed=false`.
- Actual process-death test: the worker exited after publishing a snapshot but before
  committing its DB reference; the next worker resumed and accepted the verified artifact
  once, with attempt count 2.
- CodeQL 2.26.3 created and finalized a database for one synthetic Python module on
  ARM64 (2 threads, 2 GiB configured RAM). This smoke check did **not** run vulnerability
  queries. Extractor autodetection selected host Python 3.14.5 and logged a missing-python2
  probe before succeeding; the M2 runner should explicitly bind the intended interpreter.

Runtime/demo/build artifacts are ignored by Git. The CodeQL database is under
`work/codeql-smoke-db`; it is a setup probe, not an application-produced scan report.

## Next logical slice

Add deterministic Python indexing and CodeQL extraction diagnostics, model-independent
coverage accounting, and a first evidence/report contract. Then integrate bounded
triage and materialized repository reports as described by M2. Benchmark answers must
remain outside all scan inputs when the supplied 50-repository evaluator is introduced.
