# Slice 78 — C# repair passes bounded adversarial call-binding checks

The isolated Slice 77 frontend repair passed ten additional real Joern fixture cases.
Each case checks exact internal callee identity as well as the expected flow count.
No further Joern patch was necessary, and the production application remains unchanged.

| Shape | Vulnerable / fixed flows | Exact binding |
|---|---:|---|
| File-scoped namespace | 1 / 0 | Probe.Worker.Find, string overload |
| Namespace-qualified static call | 1 / 0 | Probe.Worker.Find, string overload |
| Typed instance field call | 1 / 0 | Worker.Find, string overload |
| String/int overload declarations | 1 / 0 | Worker.Find, string overload only |
| Duplicate Worker.Find in Safe and Danger namespaces | 0 (negative) | Safe.Worker.Find only |
| Disconnected dangerous Repository.Find | 0 (negative) | Safe.Worker.Find only |

Each case retained one source, one sink and one Find call. The query requires the call's
methodFullName and sole internal callee to match the expected owner/signature. Negative
cases cannot pass by losing all bindings. This provides evidence that the small repair
retains these distinctions rather than merely producing more paths. It is not general
proof of C# dispatch correctness or a measured false-positive rate.

The matrix uses a named Lookup(name) source and CommandText assignment RHS sink.
Constants form the fixed counterparts. The namespace-qualified test uses Probe.Worker,
not global:: alias syntax. External DbConnection/DbDataReader names remain unresolved;
these tests qualify only the narrow internal-call shapes, not database or framework
identity. Interfaces, virtual dispatch, generic/optional overloads, extension methods,
aliases and larger projects still need separate assessment.

Fixtures: tests/fixtures/joern-csharp-binding, with expected cases.json.
Runner: scripts/validate_joern_csharp_binding.py. Query: scripts/joern/csharp-binding.sc.
Usage: scripts/joern/csharp-repair/BINDING.md. Raw graphs, logs and results:
work/slice78-binding. Used the isolated class override from work/slice77-build; original
Joern jars were not modified. Source hashes are checked before/after, and query and
classpath-file hashes are recorded. A classpath-file hash does not verify all referenced
classes; the trusted build receipt remains the artifact identity record.

No application build/execution, dependency download or LLM call was involved. Host network
and total process memory remain unisolated; stage timeout and requested JVM heap use the
existing harness. Returned source coordinates remain raw and unqualified.

Validation: ten flow expectations and ten exact binding checks passed with the repaired
frontend; lint, formatting and whitespace checks passed. No migration or user action is
needed. The earlier ten baseline fixture passes remain Slice 77 evidence, not rerun here.

Next: versioned per-node source mapping with repeated/multiline snippet regressions,
then bounded ASP.NET framework facts through the existing syntax parser. Upstream tests,
patch review/packaging and restricted Linux/OCP qualification remain open. Do not enable
qualified C# Joern triage yet; this is progress within the bounded repair effort.
