# Slice 42: complete Java evidence from bounded expansions

Gate version 5 can assemble complete Java file context from multiple retained snippets
and explicit evidence expansions. This removes the requirement that one snippet hold
the entire file, improving advisory coverage for larger files within existing budgets.

Only excerpts with matching snapshot, path and hash participate. Their declared line
ranges must match their contents; overlaps must agree exactly; source-line totals
must agree; every line must be present. No gaps are inferred. The assembled UTF-8
source remains capped at 16 KiB. Existing expansion limits remain unchanged: 1–4
ranges per request, at most 40 lines each, depth 2, 16 snippets, cumulative 16 KiB
source and 32 KiB envelope. Some files still cannot fit; they remain unsupported.

The parser then applies the existing narrow RequestParam/executeQuery policy. Claims
must still quote their own cited snippets and match retained flow endpoints. Expansion
does not create flow evidence, erase inherited gaps, prove reachability or enable Java
false-positive suggestions. Java readiness remains incomplete.

Validation: 391 regression tests passed, including a 60-line file assembled from
bounded excerpts, missing ranges, conflicting overlaps, mismatched hashes, inconsistent
line counts and foreign imports in expanded context. A real pinned Spring CodeQL
bundle failed without imports, then passed after expansion supplied them. Its parent
bundle remained unchanged; no provider calls occurred.

No migration or new CLI command. Gate version changes triage request identity; old
keys may conflict. Recheck explicitly with check-evidence without model spend. Existing
immutable reports and triage decisions remain unchanged. Do not change keys merely
to retry an uncertain provider response.

Next priority: separately qualified Maven/Gradle Spring extraction profiles and broader
Java evidence, then the planned C#/ASP.NET lane. L1 remains partial.
