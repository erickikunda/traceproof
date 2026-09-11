# Slice 58: JavaScript/TypeScript scan-to-report foundation

Slice 57 and approved documentation/planning updates committed as `8123997`.
This slice starts L3 with distinct JavaScript and TypeScript adapters sharing the
CodeQL JavaScript extractor. No schema migration or new runtime dependency.

## Implementation

Explicit javascript/typescript selection is supported by the existing extraction and
pipeline entry points. Auto selection works only for a single detected language;
mixed JS/TS repositories remain explicit partial scans. File counts and unselected
languages stay visible. Selected extension families are copied with snapshot digest
verification before and after extraction. Configurations, package manifests, source
maps, HTML and other-language sources are omitted; no package installation or source
build is requested. The existing Python/Java/C# copy behavior is preserved.

Separate Express/eval fixture pairs use js/code-injection from javascript-queries 2.4.5.
The TypeScript fixture has typed handler parameters. The fixed cases serialize input
rather than interpreting it as code. Source is not executed. The shared fixture runner
requires 1/0 candidates, completed analysis, correct language identity, incomplete
readiness and no model calls. Reports/SARIF remain available through existing retrieval.

## Validation

Unit tests cover adapter identities, automatic selection, mixed-language rejection,
copy isolation from package/tsconfig/HTML/other-language inputs and honest report
readiness. All 482 automated tests, Ruff checks and package/image builds passed.
JavaScript and TypeScript pairs each produced 1/0 candidates under network denial;
the C# Core regression, including its advisory gate, passed on the same image.
Timings: 28.309, 26.576, 52.806 seconds respectively. These synthetic
measurements do not qualify fleet throughput.
Image: `sha256:aff84268d1e4a2bde96f4d6502b19f1fc15b5ebd4f98c6ed92eb8c1c2aecf814`.
Artifacts: work/slice58-javascript, work/slice58-typescript and work/slice58-csharp-core.

## Boundaries

This is a source-only fixture qualification, not broad Express or TypeScript support.
Module/dependency resolution, type-checking, async flow, JSX/TSX/browser frameworks,
generated/source-map handling, semantic indexing and LLM evidence remain unqualified.
Broader suites may discover more candidates but do not enable unsupported triage rules.
Raw candidate availability is separate from qualified evidence or repository security
completion. No bank source, live model calls or image push is involved. OCP validation
remains deferred until functional POC completion.

Next: JS/TS module/context qualification and the bounded policy-registry checkpoint
approved in the implementation plan. Rust, Go and mixed-language work remain priorities.
