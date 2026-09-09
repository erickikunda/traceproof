# Slice 08 — Conservative report comparison

Slice 07 is committed as `be83047`. Migration 0005 was applied to the default local POC
database and both existing smoke-test databases. This slice begins M3.7 and adds a
snapshot-bound occurrence reference relevant to M2.7. It does not establish durable
finding families, resolution, reopening, or identity across line moves.

## Workflow

```bash
uv run traceproof compare-reports REPO_ID BASELINE_REPORT_ID CURRENT_REPORT_ID
uv run traceproof compare-reports REPO_ID BASELINE_REPORT_ID CURRENT_REPORT_ID --format markdown
```

Both inputs are exact published report IDs. Retrieval verifies ownership and each
report's digest. Comparison is read-only and deterministic for its version and inputs;
it reads no source, runs no analysis and calls no model. The result carries a content
hash, comparison version and both input IDs. Export JSON/Markdown to retain the result;
there is no separate comparison table or lookup-by-comparison-ID API in this slice.

## Matching and uncertainty

| Status | Meaning |
| --- | --- |
| `observed_in_both` | Same snapshot and exact candidate fingerprint in both reports |
| `possible_continuation` | One candidate on each side shares an unchanged file/location anchor |
| `ambiguous` | Multiple candidates share the matching anchor; all remain visible |
| `baseline_only` | Observation appears only in the baseline report; not a verified fix |
| `current_only` | Observation appears only in the current report; not necessarily a new vulnerability |

Exact matches identify observations even when scan scope is incomplete; they do not
establish vulnerability truth. An occurrence ID hashes repository, snapshot and exact
fingerprint, so repeated report versions retain that reference. It is a derived reference,
not a durable finding-family record or a replacement for the raw candidate fingerprint.

Tentative matching requires completed executions, known candidate counts and snapshots,
equal profiles and entry-query digests, and known/equal observed tool inventories. A
current report published before its baseline disables tentative matching. Publication
order is not source-revision chronology; the operator selects the intended direction.
Empty candidate inventories cannot establish tool equivalence and produce a scope gap.

An anchor includes tool name/version, rule, path, file SHA-256 and start/end lines. All
fields must be known. Matching occurs only after exact matches are accounted for. Even
a unique anchor is a suggestion: statement columns, flows, transitive query dependencies
and runtime behavior are not proven equivalent. Findings are never merged or suppressed.
Renames, shifted lines and changed files remain unmatched rather than receiving a guessed
family identity. Missing or ambiguous source mappings remain visible.

Each comparison includes scope gaps, input analysis states, known/unknown counts and
per-side row totals. Ambiguous groups include every observation; their group count is
not a finding count. The latest advisory and replay indicator from each report accompany
the occurrence reference. Every row has `resolution_verified=false`; overall
`coverage_comparable=false` explicitly reflects the unimplemented coverage proof.

JSON carries the complete comparison. Markdown escapes repository-controlled text and
includes input IDs, scope gaps and a comparison table. Both are summary projections;
the source reports retain full advisory history. No database migration is added beyond
0005. Previously published reports remain retrievable and comparable.

## Validation and remaining work

198 tests passed, including 17 new comparison cases: repeated observations/advisory
changes, unchanged-file suggestions, changed files/lines/paths, unknown tool versions,
ambiguous anchors, incompatible profiles/queries, failed scans, reversed publication
order, Markdown escaping, exact-report ownership and CLI retrieval. The inherited
duplicate ZIP fixture produces one expected warning.

Remaining work includes a reviewed finding-family model, independent validation,
coverage-compatible resolution rules, source revision chronology, benchmark metrics
and measured cache/recall behavior. This slice does not claim stable identity across
edits or any recall/precision gain. It uses no paid model calls.
