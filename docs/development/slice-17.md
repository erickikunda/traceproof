# Slice 17: benchmark dashboard CSV projections

The existing offline evaluator now renders four CSV formats without changing matching,
metrics, scorecard identity or database state:

```bash
uv run veriflow benchmark-evaluate MANIFEST LABELS PLAN --format summary-csv > summary.csv
uv run veriflow benchmark-evaluate MANIFEST LABELS PLAN --format repositories-csv > repositories.csv
uv run veriflow benchmark-evaluate MANIFEST LABELS PLAN --format labels-csv > labels.csv
uv run veriflow benchmark-evaluate MANIFEST LABELS PLAN --format candidates-csv > candidates.csv
```

Each populated row includes export schema version 1, grain, scorecard ID, evaluator
version, dataset/label versions and manifest/labels/plan digests. Join on scorecard ID
plus repository ID where relevant. Candidate fingerprints are scoped by repository and
scorecard. Do not join only on dataset name or sum summary metrics after joining detail
tables. Preserve the summary even when a detail table has no rows.

| Format | Grain / interpretation |
| --- | --- |
| summary-csv | One scorecard, recall-proxy numerator/denominator/value, completion, counts and scope |
| repositories-csv | One manifest repository, selected report, evaluation status and scope gaps |
| labels-csv | One declared label, CWE, matching status, reasons and candidate references |
| candidates-csv | One observed candidate, location-match status and unreviewed adjudication |

Nulls become empty cells; numeric zero remains zero. Arrays/objects are compact JSON
cells, not delimiter-joined strings. Booleans use Python's `True`/`False` text. Detail tables
with no rows still emit headers; their identity comes from the accompanying summary.
All cells use the existing formula-neutralization policy. A leading apostrophe added
for spreadsheet safety is a presentation escape, not a change to the canonical JSON.

Known positives lacking a selected report remain in the denominator and labels export.
Unmatched candidates remain unjudged; precision and confirmed recall stay blank/unknown.
Exports contain evaluator labels and matching metadata and need evaluator-authorized
handling; they are not the owner-facing repository summary.

JSON remains the canonical scorecard. Repeated CLI invocations reevaluate stored reports
locally; they never dispatch scans or models. Retain the JSON and verify scorecard IDs
match across exports before combining them. This slice adds no persisted benchmark
registry, asynchronous export service, HTTP endpoint or migration. Schema remains 0006.

Tests cover grain/count reconciliation, stable scorecard identity, missing reports,
unknown versus zero metrics, header-only exports, formula/multiline escaping and CLI use.
