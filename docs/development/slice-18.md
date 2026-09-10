# Slice 18: benchmark results by weakness class

Evaluator version 2 adds `weaknesses` to canonical JSON, a Markdown table, and
`benchmark-evaluate MANIFEST LABELS PLAN --format weaknesses-csv` for dashboard use.
The new table has one row per CWE found in labels, manifest weakness scope or selected
rule mappings. `selected_rule_scope` describes the configured rule mapping, not proven
coverage of that weakness.

Each row contains label status counts, a candidate-location recall-proxy numerator,
denominator and value, plus unknown precision and confirmed recall. All declared labels
remain in the denominator, including ambiguous and not-evaluable labels. Class numerators
and denominators sum to the overall metric; do not average class percentages to reproduce
the overall result. This is still location-based proxy scoring, not adjudicated quality.

Class status is `no_labels` when the denominator is zero, `incomplete` when any label is
ambiguous or not evaluable, otherwise `evaluated`. A no-label value is null/blank, never
zero or perfect recall. `evaluated` can include missed labels; it does not mean all labels
matched. Overall completion semantics are unchanged, so inspect class status separately.

CSV uses the existing version-1 export conventions and common scorecard/dataset/input
identity columns. Join class rows by scorecard ID and CWE. Markdown and existing CSV
formats still render legacy scorecards. Requesting weaknesses CSV for a legacy scorecard
fails explicitly; reevaluate pinned inputs to obtain version-2 content. Scorecard IDs
change because the new metrics and evaluator version are part of the hashed body.

No matching rules, model prompts, scans, database schema or bank benchmark data change.
Tests cover partition reconciliation, mixed label outcomes, unsupported classes, empty
classes, JSON/Markdown/CSV agreement, missing reports and legacy handling. No paid calls
are needed. This advances partial M4 quality reporting; persisted scorecards and actual
adjudicated benchmark qualification remain future work.
