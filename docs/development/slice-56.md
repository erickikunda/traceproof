# Slice 56: Narrow C# SQL advisory evidence

Slice 55 committed as `dd91abd`. This slice enables advisory evidence checks for
cs/sql-injection with explicit ASP.NET Core FromQuery syntax and CommandText assignment
syntax, anchored to a complete retained CodeQL flow. No schema migration.

## Behavior and safety boundaries

Gate 6 accepts quoted source/sink/flow claims plus an unknown guard only for review.
It never proves reachability, confirms exploitability or suppresses a candidate.
Negative advice lacks qualified guard/counterevidence vocabulary and cannot pass.
Classic FromUri/implicit action binding, raw request sources and other sink APIs stay
unqualified. Name/import observations are syntax hints, not resolved framework binding;
foreign-file shadows and runtime registrations remain outside this proof boundary.

The locked C# grammar is tree-sitter-c-sharp 0.23.5. Parsing runs in a subprocess with
16 KiB source and 50,000-node bounds, 5-second CPU and 10-second wall limits, plus a
512 MiB Linux address-space limit. Non-UTF8, malformed, preprocessor-dependent, aliased,
unsupported-import or local FromQuery-shadowed source fails closed. Only the specific
Core MVC/Builder imports and ordinary System namespace imports are accepted.

Bundle builder 5 includes whole C# files of at most 40 lines within existing cumulative
budgets. Shared source_context reconstructs larger files only from consistent excerpts
with matching path/hash/snapshot and complete line coverage, bounded to 16 KiB. Java
uses the same reconstruction helper with its prior behavior. Old bundles stay immutable.
Comparison version 8 flags evidence-policy differences. Existing provider consent,
classification, budgets and triage persistence continue to apply; no automatic calls.

## Acceptance

The Core MVC and minimal API validators build real CodeQL evidence bundles and check
synthetic decisions without a provider. Passing must retain reachability_proven=false;
negative advice must fail. The normal scan report remains incomplete and untriaged.
Unit tests cover syntax/source mismatches, shadows, aliases, missing context, source
identity differences, broken flows, parser failures/timeouts and unsupported sources.
Existing Java and Python gate tests remain regression coverage.

454 automated tests, Ruff lint/format and package/image builds passed. The real Core
MVC and minimal API pairs passed with 1/0 candidates, supported_for_review gates,
reachability_proven=false and blocked negative advice. The four-case Spring regression
also passed. Timings: 50.611, 50.591 and 54.282 seconds respectively; these are
synthetic fixture measurements, not throughput qualification.
Image: `sha256:0fa113aa9872250e6c2c41dcde0339c538e36ed1bfa5cb70e08b6b114efcaa7b`.
Artifacts: work/slice56-core, work/slice56-csharp-minimal and work/slice56-spring. No bank source, live model calls, migration
or image push. OCP validation remains deferred to functional POC completion.
