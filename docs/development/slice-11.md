# Slice 11 — Offline candidate-location scorecards

Slice 10 is committed as `dcc5ae1`. This slice begins M4.3/M4.5/M4.6/M4.7 with an
offline evaluator of existing reports. It does not run scans, calculate adjudicated
precision, or evaluate the bank's 50-repository corpus.

## Inputs and execution

```bash
uv run traceproof benchmark-schema > schemas.json
uv run traceproof --state-dir /absolute/state benchmark-evaluate \
  /absolute/manifest.json /absolute/labels.json /absolute/evaluation-plan.json
```

The evaluator uses the separate manifest and labels from Slice 10. A third strict JSON
document pins the selected reports and declared scan scope:

```json
{
  "schema_version": "1",
  "manifest_sha256": "<canonical manifest SHA-256>",
  "query_sha256": "<approved query entry SHA-256>",
  "codeql_version": "2.27.0",
  "profile": "standard",
  "rule_ids": ["py/code-injection"],
  "reports": [{"repo_id": "example", "report_id": "<exact report SHA-256>"}]
}
```

The angle-bracket values above are placeholders, not valid digests. Select one exact
report per repository; omission is allowed and creates a `report_not_selected` case.
Duplicates, foreign repositories or mismatched manifest pins fail validation. Explicit
report IDs must exist, belong to the repository and pass integrity verification; invalid
IDs are request errors rather than fabricated missing results.

Report projection version 3 adds the recorded analysis CodeQL version, including for
zero-candidate scans. Republish older report inputs to capture it. The evaluator requires
matching snapshot/profile/query/tool pins, completed static execution, known counts,
ready static-review status and a Python-only language scope. Local stored snapshot/file
digests must align with the labels. It does not execute code or verify source bytes,
symbol semantics or label truth. Transitive query-pack provenance remains incomplete.

## Matching and denominators

Evaluator version 1 supports `py/code-injection` → CWE-94 and
`py/command-line-injection` → CWE-78/CWE-88. The plan declares which of these rules were
applied under its pinned query. Other weakness classes are unevaluable in this slice.

Matching requires the same pinned repository/snapshot, source path/file digest, compatible
weakness and overlapping line ranges. Only a single label connected to a single candidate
receives `matched_location`. Multiple candidates for a label or multiple labels for a
candidate remain `ambiguous`; no arbitrary tie-break or duplicate credit is applied.
Location matching cannot prove the label's symbol or root cause. Every candidate remains
unreviewed, and matches are explicitly provisional.

| Label status | Meaning |
| --- | --- |
| `matched_location` | Unique one-to-one location match under the checked scope |
| `not_observed` | No matching candidate in an eligible report; not an adjudicated false negative |
| `ambiguous` | Potential matches require human adjudication |
| `not_evaluable` | Missing/failed/incompatible report, unsupported scope or invalid file alignment |

Candidate rows are matched, ambiguous or `unjudged`. An additional candidate is never
automatically a false positive, regardless of declared label completeness. All manifest
repositories appear in the scorecard, including those without labels or reports.

The `candidate_recall_proxy` numerator is uniquely matched locations. Its denominator
includes **all declared labels**, including ambiguous and unevaluable cases. It is null
when there are no labels. Counts remain available separately so incomplete scans cannot
silently inflate a successful-subset metric. `precision` and `confirmed_recall` remain
null. There is no statistical confidence interval or population-quality claim.

`complete` describes whether the selected scope could be evaluated without ambiguous or
unevaluable labels/repositories; it does not certify security coverage, label correctness
or scan quality. Missing cases, scope failures and ambiguity make it false. Successfully
rendering an incomplete scorecard exits zero; invalid inputs/resource limits exit nonzero.

## Outputs and bounds

JSON contains manifest/label/plan digests, effective query/tool/rule scope, per-repository
and per-label results, candidate rows and explicit numerators/denominators. Markdown
provides a shareable summary with escaped text. Root-cause descriptions, source excerpts
and adjudication references are not copied into the scorecard. Label IDs still belong
to the evaluator's authorized audience.

The content-addressed scorecard is deterministic for its evaluator version and exact
inputs. Save stdout to retain it; there is no scorecard database table or retrieval-by-ID
endpoint yet. Limits are 20,000 total candidate rows, one million potential location
comparisons and an 8 MiB JSON body. Bounds fail explicitly rather than returning truncated
metrics. No database migration beyond 0005 is required.

## Validation and remaining POC work

238 tests passed, including one-to-one ambiguity, duplicate predictions, missing/failed
reports, scope/pin mismatch, file mismatch, empty labels, unjudged predictions, bounded
matching and CLI output. The inherited duplicate ZIP fixture emits one expected warning.

A real stored-report smoke test used all three Slice 09 synthetic acceptance repositories:
one matched seed, one unevaluable seed in the parse-blocked repository, and a fixed fixture
with no labels/candidates. The proxy was 1/2, `complete=false`, and precision remained null.
This is expected workflow evidence, not a measured bank benchmark or generalized recall.
No new CodeQL or model call was made by evaluation.

Useful local work remains: reviewed finding-state/family contracts, richer structural
matching, benchmark registration and scorecard exports, rule/model coverage, and optional
second-provider integration. Live gateway validation, real corpus applicability checks,
PostgreSQL/Redis coordination and OpenShift qualification need their respective environments.
The POC has not reached the limit of what can be implemented locally.
