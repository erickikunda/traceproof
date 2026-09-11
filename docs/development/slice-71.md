# Slice 71 — Python initial Joern feasibility passed

Assessed the pinned Joern 4.0.625 macOS ARM64 Python frontend with five source-only,
dependency-free fixtures. No application code was executed or dependencies installed.
The experiment does not change the existing CodeQL Python scan or triage behavior.

| Fixture | Sources | Sinks | Flows |
|---|---:|---:|---:|
| Single-file vulnerable | 1 | 1 | 1 |
| Single-file fixed | 1 | 1 | 0 |
| Three-file vulnerable | 1 | 1 | 1 |
| Three-file fixed | 1 | 1 | 0 |
| Disconnected source and sink | 1 | 1 | 0 |

The cross-file path retains six nodes across main, service and repository modules.
All nine returned nodes across the two positive cases have code fragments matching
their reported source lines. Original source hashes were unchanged. This sample does
not establish general source-map correctness or portfolio recall/precision.

The fixture query selects lookup(input) and calls named system. It does not prove
framework entry points, OS-module ownership, shell behavior, sanitizer effectiveness
or arbitrary Python call resolution. Fixed cases substitute a constant; the disconnected
case keeps a sink in an unrelated function. No production Joern Python registration
or qualified LLM triage is enabled by these results.

Repeatable runner: `scripts/validate_joern_python.py`; usage: `scripts/joern/PYTHON.md`.
Raw results, graphs and logs: `work/slice71-python-final`. The report records query/source
hashes, pinned release identity, stage durations and source-location observations.
The version-layout check does not reverify all installed tool files. Each stage uses
a 180-second timeout and requested 2 GiB JVM heap; host network and total memory are
not isolated. Python-specific restricted Linux/OCP testing remains open.

Remaining gates include framework models, dynamic imports/decorators/inheritance,
module and sink identity, dependency resolution, parse completeness/diagnostics,
real-world scale and broader CWE coverage. Java container results do not qualify the
Python frontend. No migration, bank data, API key or user action is needed.

Validation: all five real probe expectations passed; lint, formatting and whitespace
checks passed. All 521 application tests passed (one existing duplicate-ZIP warning).

Next: JavaScript/TypeScript, Go and early C/C++ feasibility, followed by the deferred
C# investigation and a portfolio-level scanner recommendation.
