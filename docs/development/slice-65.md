# Slice 65 — Bounded Joern Spring GET / JDBC discovery model

Replaced fixture method/parameter-name selection with graph-backed selectors:
- public methods with fully qualified Spring GetMapping annotations;
- String parameters with fully qualified Spring RequestParam annotations;
- argument 1 of the exact graph method signature
  `java.sql.Statement.executeQuery:java.sql.ResultSet(java.lang.String)`.

The versioned native rule is `traceproof/joern-spring-get-jdbc-sql-v1`, and the adapter
profile is experimental-2. Retained flow construction and source binding are unchanged.
The command and feasibility runner use the same packaged query. Existing reports and
bundles are immutable; new rules never inherit CodeQL qualification.

Real Joern 4.0.625 macOS ARM64 / Temurin 22.0.2 acceptance:

| Case | Selected sources | Selected sinks | Flows |
|---|---:|---:|---:|
| Vulnerable | 1 | 1 | 1 |
| Parameterized query | 1 | 0 | 0 |
| Disconnected input | 1 | 1 | 0 |
| Renamed method and parameter | 1 | 1 | 1 |
| Foreign RequestParam annotation | 0 | 1 | 0 |
| Custom executeQuery method | 1 | 0 | 0 |
| Missing GetMapping | 0 | 1 | 0 |

The complete repeatable probe is `work/slice65-spring-model/report.json`. The renamed and
annotation-lookalike cases also ran through durable intake/discovery/report publication
in `work/slice65-durable`, with expected 1/0 candidates and incomplete review readiness.
The renamed candidate produced a Joern-tagged, unqualified evidence bundle.

This is an expanded discovery capability, not runtime Spring reachability or a complete
framework model. Graph fully qualified names do not authenticate library definitions,
bean registration or dynamic dispatch. Other mappings, parameter types, RequestBody,
custom wrappers, alternative SQL APIs and inherited/reflective calls remain unqualified.
No-hit output can reflect unsupported sources/sinks and must not become a clean verdict.
Joern remains discovery-only; no LLM, independent verification or suppression is enabled.

Validation: seven real probe cases passed, two real durable cases passed; 506 existing
unit/integration tests pass (one existing duplicate-ZIP warning). Ruff lint/format,
whitespace checks and package build pass. No migration or bank data was used.

Next: explicit Joern coverage/diagnostic accounting and restricted Linux execution,
followed by the early C#/Rust gates. Broader Spring/JDBC models should be added as
separately tested profiles, preserving unknown cases and source/sink omissions.
