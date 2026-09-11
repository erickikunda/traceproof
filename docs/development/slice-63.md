# Slice 63 — Real Joern Java cross-file feasibility

Installed Joern 4.0.625 macOS ARM64 locally under ignored `work/joern-v4.0.625/joern-cli`.
The release ZIP SHA-256 was checked against GitHub release metadata:
`86ae415d1be580681c74f08ff66579e5d1a7d6b81fb0cc5b9de61dcca9b59e5d`.
Existing CodeQL and system PATH were unchanged. The probe used the installed Temurin
22.0.2 ARM64 runtime. This does not qualify JDK 21 or a Linux distribution.

Added three Java fixtures, a trusted Scala flow query, a repeatable Python runner, and
release metadata/operator notes under `scripts/joern`. No application build or dependency
restoration was requested. All cases span controller, service and repository source files.

| Fixture | Sources | SQL argument sinks | Flows | Preparation | Analysis |
|---|---:|---:|---:|---:|---:|
| Vulnerable string-built SQL | 1 | 1 | 1 | 5.814 s | 3.796 s |
| Parameterized query | 1 | 0 | 0 | 5.526 s | 3.347 s |
| Input replaced with constant | 1 | 1 | 0 | 5.688 s | 3.510 s |

The vulnerable result retains six nodes across three files. Aggregate report nodes carry
validated fixture file/line references and source SHA-256 values. Source hashes are
checked before/after each case. Raw flows, logs, graphs and workspaces remain under
`work/slice63-joern-bound`; the aggregate report is `report.json` there.

The known source parameter is selected by method/parameter name; annotations are not
used to discover or validate Spring sources. The query matches executeQuery by name,
not resolved JDBC ownership. The fixed case tests a bound-parameter API shape, not a
complete sanitizer model. No-alert output is not a clean security verdict. These results
justify continuing the adapter, not declaring Java/Spring parity with CodeQL.

The release archive was verified during setup. The repeatable runner checks the version
jar layout but explicitly does not claim verification of every installed file. Network
isolation was not enforced, requested 2 GiB JVM heap is not total RSS containment, and
these tiny-fixture timings are not evidence of 1,000-repositories/day capacity.

Validation: real final Joern run passed 1/0/0 fixture expectations; 499 existing tests
passed with one expected duplicate-ZIP warning. Ruff lint/format, whitespace check and
package build passed. No migration, bank data or LLM call. No production backend enabled.

Next: convert this into a discovery-only Java backend with durable preparation/results,
source-bound normalization and explicit diagnostics, then qualify Spring source and JDBC
sink models with safe/misleading cases. Restrict Linux execution and exercise C#/Rust
acceptance gates before selecting Joern for the whole portfolio. Automatic reuse remains
disabled. C/C++ full support stays after the existing language work plan.

Sources: [release](https://github.com/joernio/joern/releases/tag/v4.0.625),
[script interface](https://docs.joern.io/interpreter/),
[data-flow query interface](https://docs.joern.io/cpgql/data-flow-steps/).
