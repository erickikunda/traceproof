# Slice 158 — Second review pass on the SBOM/OSV chain

A re-review of `9063d54^..61e1e31` confirmed the nine earlier fixes and raised four further
findings. All four were reproduced before being fixed and each carries a regression test.

**Nested advisory structure is now validated.** `read_record` checked only the top-level record
and its identifier. A record whose `affected` was an object rather than a list counted as loaded,
indexed nothing and still produced `evaluated_no_match`; a `versions` list containing an object
raised an uncaught `TypeError` from a set construction. The loader now validates the nested shape
matching depends on — `affected` entries, `package` fields, `versions` members, `ranges` and their
`events` — and an invalid record is counted unread rather than treated as absent evidence. The
validation was checked against the live 245,373-record export: all 244,438 non-withdrawn records
are accepted, so nothing well-formed is rejected.

**Result limits are enforced while accumulating.** `MAX_MATCHES` was applied after
`evaluate_component` had materialized every match for a component, so one component could build
hundreds of thousands of dictionaries before refusal. The limit is now checked as each match is
appended. Advisory prose is also bounded: an upstream `summary` is capped at 4,096 characters with
a `summary_truncated` marker and aliases at fifty, so a single match cannot size the output.
`export_osv` accumulates encoded bytes per source group and refuses as the bound is crossed rather
than after serializing the whole document.

**An incomplete database no longer yields fully evaluated components.** Unread records previously
downgraded only `evaluated_no_match`, so a component with a match and an unread record stayed
`matched`, counted toward `components_fully_evaluated` and carried no gap. The matched state still
stands, but `components_fully_evaluated` is zero whenever any record was unread, every affected
component carries a `component_state_database_incomplete` gap, and the CycloneDX metadata now
exposes `traceproof:osv_records_unread` and `traceproof:osv_components_fully_evaluated`. Before
this, `get-sbom --database` disclosed no incompleteness at all.

**Validation claims in the slice notes were overstated.** Slice 157 counted sixteen new tests
where the file collects fifteen, and eleven slice notes claimed that lint and formatting pass when
repository-wide Ruff reports twenty-three pre-existing errors and twenty-two unformatted files.
Every affected note now states that the changed files pass against an unchanged repository-wide
baseline, which is what was actually verified. The correction spans Slices 142 through 157, not
only the note that was flagged.

Eleven new tests. The changed files pass lint and formatting against an unchanged repository-wide
baseline, and the full suite passes: 1,312 tests. No migration and no schema change.
