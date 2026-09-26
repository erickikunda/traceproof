# C# / ASP.NET Joern feasibility gate

Run the opt-in local probe with a trusted Joern 4.0.625 installation:

```sh
uv run python scripts/validate_joern_csharp.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-csharp-new
```

The directory must be new. The script reuses stage timeouts and a restricted environment,
retains graph/log/output artifacts, verifies fixture file hashes before/after analysis,
and checks file/line references for returned nodes. It records native rule identity,
query hash, Joern version layout, source hashes and stage durations. It does not assert
installed-content integrity, network isolation, peak memory or OCP compatibility.

The query deliberately selects the fixture parameter Lookup(name) and the right-hand
side of assignments to a field named CommandText. This probes data-flow feasibility;
it does not discover framework entry points or authenticate DbCommand types. Vulnerable
and parameterized variants cover ASP.NET Core, classic MVC, classic Web API, and a custom
three-file Core-style controller/service/repository chain.

Do not register this rule as a qualified C# scanner. In the tested source-only Core graph,
FromQuery is absent from parameter annotations, HttpGet is unqualified, and DbConnection /
command calls have unresolved signatures. A correct flow does not resolve those gaps.

Next integration should evaluate reusing VeriFlow's bounded C# syntax parser for explicit
attribute/import facts, binding those facts to graph nodes by source hash and location.
Ambiguous or absent mappings must remain unsupported, and the new engine must receive its
own qualification tests rather than inherit CodeQL policy by rule name or CWE. Rust remains
an early engine-choice gate before broad backend commitment.

Slice 69 outcome: the eight-case run deliberately exits 1 because the vulnerable
three-file chain has no retained flow. Raw C# line numbers are also unqualified: all six
single-file positive nodes matched the next source line in a separate audit. The runner
marks mapping unverified; it does not silently correct coordinates. See Slice 69 before
interpreting a successful individual flow count as scanner qualification.

Slice 75 adds an explicit-namespace cross-file pair (1/0). The original global-namespace
case remains in the runner and fails. New path nodes have mixed line agreement: do not
apply a blanket +1 correction. See Slice 75 for the bounded recovery plan.
