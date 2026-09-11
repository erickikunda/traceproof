# JavaScript / TypeScript Joern feasibility probe

Run each language separately with the trusted pinned Joern 4.0.625 installation:

```sh
uv run python scripts/validate_joern_javascript.py \
  --language javascript --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-javascript-new
uv run python scripts/validate_joern_javascript.py \
  --language typescript --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-typescript-new
```

Output directories must be new. Each language has five dependency-free source fixtures:
single-file and three-file vulnerable/fixed pairs, plus disconnected source and sink.
Cross-file fixtures use ES module named imports; TypeScript adds string annotations.
The query explicitly selects lookup(input) and argument 1 of calls named eval. It is
a fixture experiment, not a framework-aware code-injection rule or complete JS/TS model.

The runner copies sources, preserves hashes, checks returned file and line bounds, and
records snippet/line agreement separately from the flow expectation. It retains CPGs,
logs, JSON, query hash, pinned release metadata and per-stage durations. Each stage has
a 180-second timeout and requested 2 GiB JVM heap. This local probe does not enforce
network isolation or total process memory; version-layout validation is not a full
installed-file integrity check. No npm install, application execution or LLM is used.

CommonJS, tsconfig path aliases, bundlers, JSX/TSX, decorators, async callbacks, framework
entry points, shadowed eval, sanitizers and dependency behavior need separate tests.
This probe does not register a production backend or enable qualified LLM triage.
