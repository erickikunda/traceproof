# Slice 139 — C# query-binding source discovery

Added `csharp-query-commandtext-v1`, replacing fixture-name source selection with
parameter flows filtered by exact mapped query-binding syntax. New-rule publication
requires a source fact on the first flow node. Existing span checks remain mandatory.
The legacy profile remains unchanged and automatic selection runs both separately.

Seven restricted repaired-frontend Linux fixtures passed: renamed Core FromQuery
action, constant query, namespaced cross-file helper, disconnected, foreign attribute,
unbound parameter and length guard. Counts 1/0/1/0/0/0/1. Native source mapping,
publication, exact retrieval and HTML/JSON/CSV checks passed with zero model calls.

Full regression run passed 1,059 tests with the existing duplicate-ZIP warning.
After adding two source-gate tests and preserving both automatic C# profiles,
13 focused C# mapping/selection tests passed. Ruff and whitespace checks passed.

Raw graph counts precede syntax filtering. CommandText remains a name-based sink;
route registration, framework/database identities and SQL execution are unverified.
New-rule advisory is unsupported. No migration or published-image promotion.
See [guide](../guides/csharp-query-discovery.md). Next C# file/process sink breadth.
