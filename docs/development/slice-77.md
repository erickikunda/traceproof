# Slice 77 — Bounded C# global-namespace repair succeeds on existing fixtures

Implemented and locally compiled an experimental one-line Joern frontend change. The
original Joern installation and all source fixtures remain unchanged. No call edges are
inferred or injected by TraceProof.

The pinned AstCreator compilation-unit path directly maps non-global-statement members
to ASTs, bypassing astForMembers. That helper marks globally declared types with the
parent metadata used by AstSummaryVisitor to build global type summaries. Routing through
the existing helper recovers the previously missed global-namespace cross-file flow.
This is evidence for a small frontend repair, not a new custom C# resolver.

| Profile | Patched vulnerable/fixed flows |
|---|---:|
| Core single file | 1 / 0 |
| Classic MVC single file | 1 / 0 |
| Classic Web API single file | 1 / 0 |
| Global-namespace three-file chain | 1 / 0 |
| Explicit-namespace three-file chain | 1 / 0 |

All ten existing flow expectations passed with the unchanged fixture query. The unpatched
global-namespace pair previously yielded 0/0; retain that baseline as a regression.
A graph audit of the initial experiment resolves both Find calls to their intended
SearchService.Find and SearchRepository.Find methods rather than unresolved stubs.
The query still selects Lookup(name) and CommandText RHS by fixture shape. A recovered
path does not establish framework entry points, effective guards or runtime reachability.
Source hashes were checked before/after by the runner. No dependencies, application
builds or LLM calls were used.

Patch and pinned source digests: scripts/joern/csharp-repair. Repeatable experimental
builder: scripts/build_joern_csharp_repair.py. It compiles a separate AstCreator class
override against installed pinned jars, recording jar/output hashes, and never rewrites
those jars. Opt-in runner flag: --experimental-classpath. This mechanism is for local
qualification, not production deployment or processing untrusted classpath files.

Raw flow results: work/slice77-csharp-final (repeatable build), with the initial experiment
in work/slice77-csharp. Compilation/probe evidence: work/slice77-repair;
repeatable builder output and receipt: work/slice77-build. Source location errors and
missing parameter annotations remain unchanged; C# remains unqualified for integration.

Next bounded step: adversarial call-binding regressions (duplicate names, overloads,
file-scoped namespaces, fully qualified/instance calls and disconnected sources), then
per-node source mapping and framework-fact qualification. Run the upstream frontend
suite and restricted Linux packaging before any production adapter registration.
Prefer upstream review/acceptance over maintaining a fork; nothing was posted upstream.

Validation: experimental compilation succeeded; ten real fixture checks passed; lint,
formatting and whitespace checks passed. No production application behavior or migration
changed. No user action is needed. This is progress within the bounded repair effort,
not completion of C# qualification.
