# Slice 26: import report inventory and dashboard export

`veriflow import-reports IMPORT_ID --limit 100 --format json` reads the runs admitted
by a CSV import in original row order. `--offset` selects the next page; limit defaults
to 100 and is bounded at 1000. JSON includes selected-page counts and `next_offset`.
`--format csv` exports one row per selected input row, including rejected/uncaptured rows.

The inventory distinguishes `intake_not_ready`, `not_analyzed`, `report_not_published`
and `published`. Publication is not a successful security verdict: analysis status,
static readiness and nullable candidate count are separate columns. Failed attempts
can have published reports. Missing values remain null in JSON and blank in CSV.

Selection uses the newest published version of the exact admitted run, only when its
attempt matches that run's latest attempt. It does not fall back to an older version,
another attempt or another run of the same repository. This is an import inventory,
not a claim to represent the repository's newest submission. Stored reports are hash
verified; corruption stops retrieval. Published advisory/review state remains as of
publication; changes after publication require a new report version.

Use returned repo/report IDs with `get-report` for full JSON, HTML or Markdown detail.
The inventory excludes source snippets and model responses. CSV uses the existing
spreadsheet formula escaping and stable columns. CSV contains selected rows only;
use JSON pagination metadata or explicitly select up to all 1000 admitted rows.

This command performs no scanning, publication, model calls or database migrations.
Each page reads one transaction; separate pages are not an atomic portfolio snapshot.
Current queries and integrity checks are suitable for bounded local POC batches;
distributed export and fleet throughput qualification remain future work.

Validation covers missing publication, failed-attempt freshness, isolation from newer
repository runs, report corruption, rejected rows, pagination, CSV escaping and CLI JSON.
