# Slice 157 — Review findings across the SBOM/OSV chain

A review of `9063d54^..HEAD` raised nine defects and one documentation inconsistency. All nine
were reproduced before being fixed, and each now carries a regression test in
`tests/test_review_regressions.py` that fails against the original code. Three affected whether a
component could be reported as cleanly evaluated, which is the property the whole chain exists to
protect.

**A component outside the export's ecosystems was reported clean.** Matching received only the
index, so an npm component evaluated against a Maven-only export was classified
`evaluated_no_match` and counted as fully evaluated. It is now `not_evaluated` with a
`component_state_ecosystem_not_in_database` gap. Every Go test in the suite had been matching
against a fixture declaring only npm and Maven, which is the same defect in miniature; the fixture
now declares Go.

**Unreadable advisory records no longer permit a clean classification.** `build_index` counted
`not_json`, `oversized`, `unreadable`, `unrecognized_shape` and duplicate-identifier skips, but
matching ignored them. A database with one malformed record still reported `evaluated_no_match`.
Unread records now force `partially_evaluated` with a `component_state_database_incomplete` gap
per affected component and a `database_records_unread` count in coverage. A withdrawn advisory
remains a deliberate exclusion rather than unread evidence, and still allows a clean result.

**Excess matches refuse rather than truncate.** `del matches[MAX_MATCHES:]` discarded candidates
silently; the export now refuses, because publishing a partial vulnerability result is worse than
publishing none.

**A managed range is no longer reported as a version.** A dependency inheriting `[1,2)` from local
`dependencyManagement` was emitted with `version="[1,2)"` and a PURL to match. It is now
`declared_range` with no version, so matching treats it as unresolved.

**Inapplicable Go replacements no longer invent components.** Every non-local replacement target
was emitted regardless of whether the replacement applied to any requirement, so a replacement
naming `v9.9.9` produced a phantom component while the module actually required `v3.0.0`. Targets
are now emitted only for replacements that apply, and the phantom could have produced false OSV
matches.

**Declaration limits refuse rather than truncate.** Go kept the first 5,000 requirements and Maven
stopped emitting after 5,000 dependencies, both silently, contradicting the roadmap's own
requirement. Both now refuse.

**Version fields are bounded before integer conversion.** A numeric segment longer than Python's
integer-conversion limit raised an uncaught `ValueError` from a lockfile or POM. Semantic-version
and Maven ordering now bound version text at 256 characters and return no ordering rather than
raise, and the Go parser rejects an unbounded version outright.

**The OSV output limit is enforced.** `MAX_OSV_BYTES` was declared and never referenced.

**The CycloneDX metadata no longer denies analysis the document carries.**
`veriflow:vulnerability_analysis` was always `not_included`, even beside a populated
`vulnerabilities` array; it now reports `osv_version_range_matching` when a database was consulted.

The design table listed OSV acquisition container qualification as outstanding while the same
revision recorded it complete; the table now lists native amd64 execution and the OCP acceptance
items, which are what actually remain.

Fifteen new tests. The changed files pass lint and formatting against an unchanged repository-wide
baseline, and the full suite passes: 1,301 tests. No migration and no schema change. Several of
these changes make previously clean results report gaps, which is the intent: the affected outputs
were asserting more than the evidence supported.