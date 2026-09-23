# Slice 19: durable benchmark scorecards

Migration 0007 adds `benchmark_scorecards`, keyed by canonical scorecard content hash.

```bash
uv run veriflow init
uv run veriflow benchmark-publish MANIFEST LABELS PLAN
uv run veriflow benchmark-history DATASET_ID --limit 100
uv run veriflow benchmark-get DATASET_ID SCORECARD_ID --format markdown
uv run veriflow benchmark-get DATASET_ID SCORECARD_ID --format weaknesses-csv
```

Publication evaluates pinned inputs under the local single-worker lock and commits one
scorecard atomically. Identical content reuses the existing record; changed content
creates another publication. Incomplete evaluations can be published. Input validation
failures create no publication. `benchmark-evaluate` remains nonpersisting.

Exact retrieval checks dataset ownership and content hash, supports all seven render
formats, and reads no original inputs or repository reports. It invokes neither
evaluation nor models. Application operations never update published content; the local
database owner can alter it, which integrity checks detect. This is not authenticated
enterprise storage.

History includes publication time, dataset/evaluator versions and completion, with
offset/limit/total/next_offset. Maximum page size is 1000; new publications can shift offset
pages. Unknown datasets have empty histories because there is no dataset registry yet.
No implicit latest-success selection hides incomplete publications.

Scorecards retain evaluator label IDs and match metadata and require evaluator-authorized
handling. They do not replace retaining the original approved input contracts. No corpus
registration, benchmark scan dispatch or adjudicated quality qualification is added.

Tests cover publication reuse, changed evaluations, input-free retrieval, all formats,
dataset checks, tamper detection and repeatable migration from 0006 preserving reports.
Tests use isolated state. Run `init` to upgrade the default operator database before
using the new commands.
