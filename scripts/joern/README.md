# Joern Java feasibility probe

This opt-in probe runs only the checked-in synthetic fixtures. It is not a TraceProof
scan backend and does not call an LLM. The packaged Scala query selects String RequestParam parameters on public GetMapping
methods using fully qualified graph annotation names, and matches the exact JDBC
Statement.executeQuery(String) graph signature. This is bounded discovery; it does not
qualify runtime bean wiring, reflected calls, custom JDBC wrappers or library authenticity.
Do not treat it as a production-qualified vulnerability rule.

The pinned macOS ARM64 release is in `release.json`. Download its URL, verify the SHA-256,
and extract under an operator tooling directory (the local run used ignored
`work/joern-v4.0.625/joern-cli`). Preserve executable permissions. The Joern launchers
require GNU `greadlink` on macOS. No global PATH or existing CodeQL installation changes
are needed. The validation script checks the expected version's jar filename; this is
not verification of all installed files. Archive digest verification is a separate step.

Run from the project root:

```sh
uv run python scripts/validate_joern.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --output work/joern-java-probe-new
```

Output must be a new directory. Each case retains its prepared graph, raw flow JSON,
preparation/analysis logs, and Joern workspace. `report.json` records source hashes,
query hash, runtime, release metadata, timing and bounded fixture expectations. Nodes
in the aggregate report have validated file/line references and fixture source hashes;
this is not full expression equivalence or runtime reachability verification.

Each stage has a 180-second process-group timeout. The requested JVM heap is 2 GiB;
it is not an aggregate process-memory limit. The runner uses a restricted environment
but does not isolate network access. No application build or dependency restoration
is requested. Synthetic unresolved Spring imports are intentional.

Expected results: vulnerable and renamed have one source-to-SQL-argument flow; fixed,
disconnected, annotation-lookalike, sink-lookalike and unmapped-route have zero. The fixed example uses a bound parameter and no argument to
`executeQuery`; a zero result does not establish comprehensive sanitizer modeling.
The disconnected case still contains a dangerous string-built SQL call, but receives a
constant rather than the selected input. These cases probe cross-file flow retention
and basic separation, not language-wide recall or precision.

Next qualification must broaden framework-source and sink coverage and address
unknown library semantics, additional safe/misleading variants, source snapshots,
normalized diagnostics, restricted Linux execution, and the approved benchmark corpus.
