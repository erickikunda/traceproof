# Slice 36: conservative Flask request alias evidence

Evidence gate version 3 recognizes imports such as `from flask import request as req`
when a retained CodeQL flow starts at that import and reaches `req.args`, `req.form`,
`req.data`, `req.json` or a `req.get_json()` call before a supported sink.

The complete bounded file must be reconstructable from consistent, pinned excerpts.
There must be a single simple request receiver at the source location, exactly one
top-level absolute Flask request import for that binding and a complete retained import
prefix on the same flow. Assignments, parameter shadowing, deletion, competing imports,
wildcard imports, definitions, exception bindings and pattern bindings reject the alias
mapping. Dynamic receiver expressions and ambiguous same-line receivers remain unsupported.
An alias at an unmodeled flow shape does not gain a synthetic source edge.

Accepted mappings expose `binding_name` for aliases and retain `binding_proven: false`.
This is support for advisory review of an existing CodeQL candidate, not an independent
discovery path, proof of reachability or a true-positive determination. No candidate is
removed, and guard/counterevidence obligations remain. A rebound or lookalike alias stays
insufficient evidence rather than receiving a safe verdict. Existing unaliased behavior
is retained except ambiguous modeled receiver locations now fail conservatively.

Gate version participates in triage request identity. Reusing an old key across this
upgrade can produce a conflict; old ledger entries and immutable reports are unchanged.
Use `check-evidence` for an explicit local recheck, or deliberately request new triage
under a new key and the existing budget if fresh model advice is intended. Do not change
keys merely to retry an uncertain provider response. No migration or live calls are needed.

Tests extend the retained-flow regression fixture with alias acceptance, rebinding and
shadowing lookalikes, wrong imports, missing full-file context, broken prefixes and multiple
receivers. They verify supported-for-review only and no bundle mutation. This slice does
not claim measured recall improvement on the bank corpus or a new real CodeQL fixture run.
