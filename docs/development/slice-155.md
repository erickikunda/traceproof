# Slice 155 — End-to-end scan against the live database

Ran the whole SBOM/OSV chain against a synthetic repository and the acquired 245,373-record OSV
export, exercising intake, file inventory, npm/Maven/Go declaration discovery, matching, import
evidence, Go symbol evidence and caching through the real CLI. Two defects surfaced that the unit
suite could not reach.

**`--cache` was never registered on `get-sbom`.** The Slice 152 edit that added it matched nothing,
because the target had already been reflowed onto one line, and that replacement was not asserted.
`get-osv` received the options; `get-sbom` silently did not. Every cache test called `export_sbom`
directly, so no test crossed the CLI boundary. Fixed, with two regression tests: one invoking both
commands through `CliRunner`, one asserting each command's `--help` lists the options its function
declares.

**The OSV-shaped export named Go modules with Maven's separator**, emitting
`code.sajari.com:docconv` where a Go module path is `code.sajari.com/docconv`. The name is now
chosen per ecosystem.

The scan reproduced every designed behaviour on real advisories. `lodash@4.17.20` matched five
records by semantic-version range and `jackson-databind@2.9.8` matched fifty-five by exact version
list, the latter resolved from a `${jackson.version}` property. `code.sajari.com/docconv@v1.2.0`
matched four records with the `v` prefix stripped, and Go symbol evidence separated them into one
`symbol_referenced` where the source calls `docconv.Convert`, one `package_not_imported`, and two
`no_symbol_data` from advisories carrying no import data. An `aahframe.work` requirement under a
`replace` directive carried no version and was never matched, as was an `slf4j-api` dependency with
no version. Component states reconcile exactly: three matched, three evaluated with no match, four
never evaluated, against ten declared components.

The Maven groupId-prefix limitation appeared exactly as documented. The fixture imports
`com.fasterxml.jackson.databind.ObjectMapper` while the dependency's groupId is
`com.fasterxml.jackson.core`, so a genuinely used library reports `not_observed`. That is the
documented convention failing on a real coordinate, not a defect.

Cache timings through the CLI were 55.06 seconds cold against 2.34 seconds warm, and the two
documents differed by four bytes — `reverified` against `cached`. The 2.34 seconds is lower than
the 10.5 seconds recorded in Slice 152, which was measured in a process that had already built the
index twice; the clean-process figure is the one to trust. All sixty-four candidates remained
`in_triage`.

**The Maven `ECOSYSTEM` range ordering was not exercised end to end.** Every Maven advisory matched
here carried an explicit `versions` array, so the `ComparableVersion` path never ran; it remains
covered by unit tests only. No scanner backend ran, no model was called, and nothing here
establishes exploitability. The figures come from one live export on one machine. The changed files
pass lint and formatting against an unchanged repository-wide baseline, and the full suite passes:
1,282 tests.

Next: native amd64 execution and the OCP acceptance items, both cluster environment work.
