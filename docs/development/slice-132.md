# Slice 132 — deterministic automatic scan selection

The main CLI scan commands now default to automatic language selection and, for
Joern, all bounded profiles. Sequential mixed-language dispatch returns separate
report IDs and explicit unsupported/error scopes. Explicit profile overrides,
profile-aware retry suppression and discovery-only budget behavior are retained.

See [operator guide](../guides/automatic-scan-selection.md). Direct API defaults and
container entrypoints are unchanged. No migration is required.

Validation: inventory/override/no-source/advisory/failure-continuation tests; full
regression suite; packaged-wheel restricted Linux native Python automatic selection
and retry validation. Native acceptance runs all four Python profiles against the
SQL fixture and retrieves each report. This does not qualify mixed-language data
flow, additional CWEs, OCP cluster operation or production throughput.

Next: revisit useful detection breadth across the remaining languages using the
CWE roadmap; prioritize functional gaps before CLI or extraction optimization.

Validation results: native four-profile discovery/retry passed with zero model calls.
Initial full suite: 1,055 passed and one existing advisory CLI test required the new
explicit `default` profile. After updating that contract, all 16 focused selection
and advisory tests passed. Ruff and diff whitespace checks passed.
