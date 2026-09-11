# Slice 74 — Early C/C++ Joern feasibility passed

Assessed pinned Joern 4.0.625 macOS ARM64 c2cpg separately against .c and .cpp fixtures.
Each cross-file chain has three translation units and a shared declaration header.
C++ fixtures use the common C/C++ subset; these results do not qualify C++-specific
object models, templates or virtual dispatch. No application build or execution,
compilation database, dependency installation or LLM was involved.

| Fixture | C flows | C++ flows |
|---|---:|---:|
| Single-file vulnerable | 1 | 1 |
| Single-file fixed | 0 | 0 |
| Three-file vulnerable | 1 | 1 |
| Three-file fixed | 0 | 0 |
| Disconnected source and sink | 0 | 0 |

Every case retained one source and one sink. Each cross-file positive has six path
nodes across main, service and repository. All sixteen returned nodes across the four
positive cases match their reported source lines; original copied hashes are unchanged.
This is fixture feasibility, not measured portfolio recall/precision or full support.

The query selects lookup(input) and calls named system. It proves neither external
input binding nor runtime reachability, standard-library ownership, effective guards
or memory-safety detection. The positive entry function need not be called at runtime;
this probe deliberately tests parameter-to-sink data flow. Fixed cases substitute a
constant and disconnected cases keep the sink in an unrelated function.

Runner: `scripts/validate_joern_c_family.py`; usage: `scripts/joern/C-FAMILY.md`.
Raw graph/log/JSON evidence: `work/slice74-c` and `work/slice74-cpp`. Reports include
language, query/source hashes, release metadata, stage durations and source locations.
Pinned-layout checking is not full installed-content verification. Each stage requests
2 GiB JVM heap and has a 180-second timeout; host network and total memory are not
isolated. Java restricted-container acceptance does not qualify C/C++ under Linux/OCP.

Remaining work includes compilation settings, macros/includes, aliasing, C++ language
features, memory-safety rules, parser completeness, larger repositories and restricted
Linux/OCP qualification. No production backend or qualified LLM triage is enabled.
Full C/C++ implementation remains after the existing language plan.

Validation: all ten real expectations and sample source-line checks passed. Lint,
formatting and whitespace checks passed. Application behavior is unchanged; no migration
or user action is required.

The initial assessment now has evidence for all planned languages. C# is the only
observed failed initial flow gate; other passes remain explicitly narrow. Next revisit
its unresolved cross-file calls, missing framework metadata and source-line mismatch,
retaining the failed regressions. Evaluate targeted repair before choosing a fallback;
do not manufacture missing flow evidence or silently adjust all source coordinates.
