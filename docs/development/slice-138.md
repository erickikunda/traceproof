# Slice 138 — Java shell command discovery

Added `java-spring-runtime-shell-v1` with separate CWE-78 rule/report identity and
automatic Java selection. Exact Runtime.exec(String[]) signature, inline three-element
array, supported literal shell and -c are required. Only command text is the sink;
ordinary executable arguments and extra-element shell arrays are excluded.

Eight restricted Linux native fixtures passed: direct, constant, cross-file,
disconnected, unrelated exec method, length guard, ordinary argument and shell
positional argument. Counts: 1/0/1/0/0/1/0/0. Normal source-location validation,
publication, exact report retrieval and HTML/JSON/CSV checks passed. Zero model calls.
36 focused selection, pipeline and advisory regression tests passed. Ruff and diff
whitespace checks passed; code index refreshed.

Discovery only: executable identity, guards and runtime exploitability unverified.
No new advisory qualification, database migration or published-image rebuild.
See [guide](../guides/java-shell-discovery.md).

Next: practical C#/ASP.NET request-source breadth, addressing the legacy Lookup
source limitation before adding more synthetic-source detectors.
