# Python Joern feasibility probe

Run with the trusted pinned Joern 4.0.625 macOS ARM64 installation:

```sh
uv run python scripts/validate_joern_python.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-python-new
```

The output directory must be new. Five copied, dependency-free fixtures exercise
single-file and three-file vulnerable/fixed pairs and a disconnected source/sink.
The source is the named `lookup(input)` parameter; the sink is argument 1 of calls
named `system`. This deliberately narrow query does not establish OS-module ownership,
web input recognition, sanitizer behavior or a production command-injection rule.

The runner retains graph, logs and JSON; checks original file hashes and path/line
bounds; and records snippet/line agreement separately from the flow expectation.
It records pinned version layout, query hash and stage durations. Each stage has a
180-second timeout and requested 2 GiB JVM heap. Environment variables are allowlisted;
network isolation and a total process-memory limit are not enforced on this host.
Fixtures are statically parsed, not executed; no application package installation or
LLM calls are needed. This is an opt-in assessment, not a registered Python backend.

Results are fixture observations, not measured recall/precision on real repositories.
Frameworks, dynamic imports, inheritance, decorators, aliases, dependency resolution,
parser diagnostics, larger projects and restricted Linux/OCP execution remain open.
