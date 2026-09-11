# Adversarial call-binding fixture matrix

After building the experimental Slice 77 repair, run:

```sh
uv run python scripts/validate_joern_csharp_binding.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --experimental-classpath work/slice77-build/patched-classpath.txt \
  --output work/csharp-binding-new
```

The output directory must be new. The matrix includes file-scoped namespaces, explicit
namespace-qualified static calls, typed instance fields, a string/int overload pair,
and disconnected safe/dangerous methods with matching names. Positive and constant
counterparts use the same source/sink query shape as earlier experiments.

Each case checks one source, one sink, the exact expected flow count, exactly one Find
call, and its exact internal callee identity/signature. A zero-flow negative cannot pass
by losing its safe call binding. Namespaced duplicate classes must bind only to Safe.Worker.
Fixtures use unresolved external DbConnection/DbDataReader names; their internal binding
checks do not qualify database API identity. Interface/virtual dispatch, generic overloads,
optional arguments, extension methods, global:: aliases and real projects remain outside
this matrix. Namespace-qualified calls here use Probe.Worker, not global:: syntax.

The runner copies sources, checks hashes, retains CPG/native JSON/logs, and records query
and classpath-file hashes. The latter is not verification of all referenced classes/jars;
use the trusted isolated build and its receipt. Stage timeouts and requested JVM heap
reuse the earlier local harness. Network/total process memory are not isolated. Source
coordinates remain raw and unqualified; no application compilation/execution or LLM is
involved. No production C# adapter is enabled by a passing matrix.
