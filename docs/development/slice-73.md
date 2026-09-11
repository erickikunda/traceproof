# Slice 73 — Go initial Joern feasibility passed

Assessed pinned Joern 4.0.625 macOS ARM64 with five dependency-free Go module fixtures.
The cross-file pair crosses three packages using module-qualified imports. The host has
Go 1.26.7 darwin/arm64; no application compilation or execution was requested. Source
preparation uses gosrc2cpg; no third-party dependencies or LLM calls were involved.

| Fixture | Sources | Sinks | Flows |
|---|---:|---:|---:|
| Single-file vulnerable | 1 | 1 | 1 |
| Single-file fixed | 1 | 1 | 0 |
| Three-package vulnerable | 1 | 1 | 1 |
| Three-package fixed | 1 | 1 | 0 |
| Disconnected source and sink | 1 | 1 | 0 |

The cross-package path retains six nodes across main, service and repository. All eight
returned nodes across the positive cases match their reported source lines. Original
copied source hashes remained unchanged. This does not establish general source-map
accuracy or portfolio recall/precision.

The query selects lookup(input) and argument 3 of calls named Command. It does not
establish os/exec ownership, shell execution semantics, framework request binding or
sanitizer effectiveness. Fixed cases substitute a constant argument; the disconnected
case retains a sink in an unrelated function. No production Go backend or qualified
LLM evidence policy is enabled.

Runner: `scripts/validate_joern_go.py`; usage: `scripts/joern/GO.md`. Raw graphs, logs and
JSON: `work/slice73-go`. Reports preserve query/source hashes, pinned release identity,
stage durations and source-line observations. A version-layout check is not full
installed-content verification. Each stage has a 180-second timeout and requested 2 GiB
JVM heap. GOPROXY/GOSUMDB are off and GOTOOLCHAIN is local; OS network isolation and total
process-memory enforcement are absent in this host probe.

Remaining gates: interfaces, method receivers, generics, goroutines/channels, build tags,
cgo, external dependencies, framework models, parser completeness/diagnostics, larger
repositories and restricted Linux/OCP runtime qualification. Java container acceptance
does not qualify this frontend. No migration or user action is required.

Validation: all five real flow expectations passed; sample source locations matched.
Lint, formatting and whitespace checks passed. Application behavior is unchanged.

Next: early C/C++ feasibility, then deferred C# investigation and portfolio-level scanner
recommendation. Full C/C++ implementation remains after the existing language plan.
