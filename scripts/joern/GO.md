# Go Joern feasibility probe

Run with the trusted pinned Joern 4.0.625 macOS ARM64 installation:

```sh
uv run python scripts/validate_joern_go.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-go-new
```

The output directory must be new. Five fixtures include single-file and three-package
vulnerable/fixed pairs and a disconnected source/sink. Each has a local go.mod and no
third-party dependencies. Fixtures are parsed, not executed; no shell payload is run.
The named lookup(input) parameter is the source; argument 3 of calls named Command is
the sink. This does not establish os/exec ownership, shell semantics or web input binding.

The runner copies and hashes sources, retains graph/log/JSON artifacts and records
query hash, release metadata, stage durations and snippet/line agreement. Flow expectations
are separate from source-location observations. A 180-second timeout applies per stage;
2 GiB JVM heap is requested. Network and total process memory are not isolated on the
host. GOPROXY/GOSUMDB are off and GOTOOLCHAIN is local; these settings are not OS network
denial. The pinned-layout check does not verify every installed Joern file.

Interfaces, method receivers, generics, goroutines/channels, build tags, cgo, framework
models, dependency resolution, parse completeness and restricted Linux/OCP behavior
remain separate qualification work. No production Go backend or LLM triage is enabled.
