# Slice 75 — C# investigation and recommended recovery path

Recommendation: retain Joern as a C# qualification candidate and pursue a bounded,
regression-driven frontend/integration repair before adopting a replacement. Keep CodeQL
as the working POC reference within existing authorization. Do not enable qualified
Joern C# triage yet. The evidence narrows the failure but does not resolve it.

## New local evidence

Using the unchanged pinned Joern 4.0.625 and unchanged fixture query, copied the previous
three-file controller/service/repository pair and enclosed the classes in the explicit
TraceProofProbe namespace. No dependencies were downloaded or application builds run.

| Cross-file variant | Vulnerable flows | Fixed flows |
|---|---:|---:|
| Original global namespace (Slice 69) | 0 | 0 |
| Explicit namespace (Slice 75) | 1 | 0 |

The new positive contains six nodes across three files. Four snippets match the line
after the raw reported line; two match the reported line itself. A uniform +1 adjustment
would therefore break correct coordinates. Parameter annotations remain absent in the
query result. Explicit namespace success does not establish broad C# call resolution.

This is a controlled diagnostic source variant, not a proposal to rewrite scanned
repositories. Original global-namespace fixtures remain unchanged and failing. Added
namespaced fixtures to the repeatable C# runner, which still intentionally fails if
the original vulnerable flow is missed. Raw new probe evidence: work/slice75-csharp.

## Investigation and implementation order

1. Diagnose global-namespace symbol resolution in the pinned frontend. Expand the matrix
   to block/file-scoped namespaces, fully qualified calls, duplicate class/method names,
   overloads, instance calls and interfaces. Confirm callee identity, not only flow counts.
   Prefer a small upstreamable fix or qualified pinned upgrade over a permanent custom
   resolver. Do not insert guessed call edges based on method-name matching.
2. Add a versioned source-mapping layer that retains raw coordinates and source hashes.
   Validate each node against syntax spans and context. Preserve ambiguous/missing mappings
   as unsupported; never silently apply an engine-wide line offset. Include repeated
   snippets, multiline expressions, comments and attributes in regression tests.
3. Reuse the existing bounded C# syntax parser for explicit ASP.NET attributes/imports,
   joined only through validated source mappings. Syntax facts do not replace missing
   interprocedural flow or prove runtime reachability. Keep separate engine policy gates.
4. Evaluate trusted offline external type summaries where dependency symbols are needed.
   Local csharpsrc2cpg --help exposes --external-summary-paths and --download-dependencies.
   Prefer pinned summaries/artifacts on PVC; do not default to network dependency restore.
   DLL/reference downloads alone are not an established fix for the observed local-call
   failure. Summary generation and its inputs still need reproducible qualification.
5. Run the repaired profiles in the restricted Linux image, then the authorized benchmark
   and later bank OCP. Namespace success alone does not qualify Classic ASP.NET or all C#.

Proposed decision checkpoint: two implementation slices for diagnosis/minimal repair and
regression/source-mapping qualification. This is a scope limit, not a promised duration.
If this cannot recover trustworthy paths without maintaining a substantial resolver,
reconsider a dedicated C# semantic component (for example a separately assessed Roslyn
sidecar) or another backend. Do not commit now to building a new whole-program analyzer.
Any fallback must prove cross-file behavior, precision, deployment and license fit; a
candidate-only scanner can supplement findings but cannot claim missing-flow parity.

## Primary-source inspection

Inspected the pinned upstream frontend source locally. Invocation construction uses an
unresolved namespace when the base type is absent, consistent with the original graph;
this supports investigating symbol resolution, but does not identify a proven patch.
The node-info helper consumes LineStart/LineEnd metadata directly. Neither observation
justifies guessing a universal repair.

- [Invocation construction](https://github.com/joernio/joern/blob/v4.0.625/joern-cli/frontends/csharpsrc2cpg/src/main/scala/io/joern/csharpsrc2cpg/astcreation/AstForExpressionsCreator.scala)
- [Node metadata](https://github.com/joernio/joern/blob/v4.0.625/joern-cli/frontends/csharpsrc2cpg/src/main/scala/io/joern/csharpsrc2cpg/astcreation/AstCreatorHelper.scala)
- [C# scope](https://github.com/joernio/joern/blob/v4.0.625/joern-cli/frontends/csharpsrc2cpg/src/main/scala/io/joern/csharpsrc2cpg/datastructures/CSharpScope.scala)

Validation: the new namespace pair produced 1/0 in real local runs; mixed coordinate
observations were audited from the retained source. No production code, migration or
backend registration changed. No user action is required. No issue was posted upstream.
