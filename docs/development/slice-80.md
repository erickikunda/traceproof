# Slice 80 — Bounded C# framework syntax facts joined to validated spans

Added opt-in framework facts to the experimental source-location validator. The existing
C# syntax parser can now return byte spans when requested; its default line-only output
is unchanged. Facts are computed inside the same bounded child process as location
validation and attach only when the validated node span is contained in the fact's byte
range for the same hashed source. A shared line number alone is never sufficient.

Recognized observations are explicit FromQuery parameter syntax, the existing bounded
classic MVC/Web API HttpGet parameter shape, and CommandText assignment RHS syntax.
These do not establish runtime request binding, resolved framework/database symbols,
route reachability, guard effectiveness or complete flow. Core FromQuery is labeled as
an explicit annotation observation, not a fully qualified endpoint. Local-file alias,
preprocessor and known lookalike restrictions reuse the existing parser. Cross-file
lookalikes and broader symbol ambiguity remain unqualified.

The source-span profile is now joern-csharp-span-2. It additionally recognizes the
syntax-derived type-to-name subspan of an attributed parameter, because Joern may omit
attributes from its code property. This uses parser byte boundaries rather than stripping
text or moving line numbers heuristically. Original spans and raw coordinates remain
preserved; repeated candidates still yield ambiguity and receive no facts.

Replayed all 18 path nodes from the five positive repaired baseline cases: all obtained
unique spans. Source facts attach to Core and classic source nodes, sink facts to the
five CommandText RHS nodes, and intermediate service/repository parameters receive no
framework fact. Some graph nodes refer to the same source parameter; attached observations
are not distinct vulnerability counts. This replay uses retained real Joern output;
no new scanner execution was necessary.

Replay command:

```sh
uv run python scripts/validate_csharp_locations.py \
  --input work/slice77-csharp-final --fixtures-root tests/fixtures \
  --framework-facts --output work/framework-span-audit-new.json
```

Raw audit: work/slice80-framework-final.json. Output must be new; replay inputs are trusted
local harness data, not a public report-upload interface. Source hashes and path
containment are checked. Parser limits remain those of Slice 79.

Six added regression tests cover attributed parameter subspans, two parameters on the
same line, repeated/ambiguous declarations, sink RHS containment, classic fixture facts,
unchanged legacy output, aliases/local attribute lookalikes and hash mismatch. All 533
tests passed (one existing duplicate-ZIP warning), plus lint/format and whitespace checks.

No production backend or triage gate is promoted. Next validate the repaired frontend,
source mapping and fact attachment in the restricted Linux container, preserving explicit
coverage limits. Upstream packaging/review and later bank OCP acceptance remain open.
No migration, LLM call or user action is required. Changes remain uncommitted.
