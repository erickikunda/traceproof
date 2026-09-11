# Slice 72 — JavaScript/TypeScript initial Joern feasibility passed

Assessed the pinned Joern 4.0.625 macOS ARM64 JavaScript frontend separately against
JavaScript and TypeScript fixtures. TypeScript uses explicit string parameters; both
languages use ES module named imports for the cross-file chain. No npm dependencies
were installed, application code executed or LLM calls made.

| Fixture | JavaScript flows | TypeScript flows |
|---|---:|---:|
| Single-file vulnerable | 1 | 1 |
| Single-file fixed | 0 | 0 |
| Three-file vulnerable | 1 | 1 |
| Three-file fixed | 0 | 0 |
| Disconnected source and sink | 0 | 0 |

Each case had one modeled source and one sink. Each cross-file positive retained six
nodes across main, service and repository. All 18 returned nodes across the four
positive cases matched their reported source lines; copied source hashes were unchanged.
These results establish initial fixture feasibility, not portfolio recall/precision.

The query selects lookup(input) and calls named eval. It does not establish request
binding, built-in eval ownership, effective sanitization or runtime reachability.
Fixed cases replace the eval argument with a constant, while disconnected cases put
the sink in an unrelated function. Shadowed eval and framework lookalikes are untested.

Repeatable runner: `scripts/validate_joern_javascript.py`, with an explicit language
selector; instructions: `scripts/joern/JAVASCRIPT.md`. Raw results/logs/graphs:
`work/slice72-javascript` and `work/slice72-typescript`. Reports preserve language,
query/source hashes, pinned release metadata, stage durations and source-line checks.
Host network and total process memory are not isolated; requested heap is 2 GiB and
each stage has a 180-second timeout. Version-layout validation is not full integrity
verification. Java-only restricted Linux results do not qualify these frontends.

Remaining gates: CommonJS, tsconfig aliases, JSX/TSX, async callbacks, decorators,
dependency resolution, framework source/sink identity, parser completeness and
restricted Linux/OCP runtime behavior. No production Joern JS/TS backend or qualified
triage is enabled; existing CodeQL behavior remains unchanged. No migration is needed.

Validation: all ten real flow expectations passed, with matching sample source lines.
Lint, formatting and whitespace checks passed. No user action is required.

Next: Go, then early C/C++ feasibility, then the deferred C# investigation and
portfolio-level scanner recommendation. Full C/C++ implementation remains later.
