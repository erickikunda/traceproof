# Early C / C++ Joern feasibility probe

Run each input mode separately with the trusted pinned Joern 4.0.625 installation:

```sh
uv run python scripts/validate_joern_c_family.py \
  --language c --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-c-new
uv run python scripts/validate_joern_c_family.py \
  --language cpp --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-cpp-new
```

Output directories must be new. Each mode has single-file and three-translation-unit
vulnerable/fixed pairs, plus a disconnected source and sink. The cross-file pair has a
shared header with declarations. The C++ fixtures intentionally use the common C/C++
subset with .cpp files: success does not qualify classes, templates or C++ dispatch.

The source is lookup(input); the sink is argument 1 of calls named system. This is a
bounded flow probe, not a complete command-injection rule, memory-safety analysis or
runtime-reachability proof. Nothing invokes lookup or executes the fixture programs.
No compilation database, application build, package installation or LLM is used.

The runner copies/hashes sources, checks returned paths and line bounds, records
snippet/line agreement separately from flow expectations, and retains graphs/logs/JSON.
Reports include query/source hashes, release identity and stage durations. The local
probe requests a 2 GiB JVM heap and enforces a 180-second timeout per stage; network
and total process memory are not isolated. Pinned layout is not full installed-file
verification. Compile flags, macros, include resolution, templates, aliasing, virtual
dispatch, memory safety and restricted Linux/OCP execution need further qualification.
