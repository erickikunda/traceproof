# Slice 79 — Conservative C# source-span validation

Added an experimental, versioned source-location validator in csharp_locations.py.
It validates source bytes against the expected SHA-256, parses C# in an isolated child,
and compares each graph snippet with complete allowed named syntax spans. It evaluates
both the raw line and the following line because the pinned frontend exhibits mixed
coordinates. Exactly one distinct matching span is required. Multiple matches remain
ambiguous; absent matches remain unsupported. No global line offset is applied.

Results preserve the raw node and separately record validated byte offsets, start/end
lines, syntax kind, source hash and line delta. This is syntax-span consistency only:
it does not prove graph-node identity, correct call binding, framework semantics or
runtime reachability. No production evidence/triage gate consumes it yet. The profile
is intended for the currently assessed Joern 4.0.625 experimental frontend; other versions
require fresh qualification rather than assuming the same coordinate behavior.

The validator excludes comment, string and attribute subtrees as standalone anchors,
while allowing full expression spans containing literals. It requires exact bytes,
including whitespace; reformatted/generated graph snippets remain unsupported. Candidate
search is limited to the two observed start lines, not the whole file. Repeated spans
on either candidate line are rejected, even when one would preserve the raw coordinate.
These conservative rules favor withholding evidence over assigning a plausible location.

## Validation

Replayed all 16 retained path nodes from the four positive Slice 78 cases against their
hashed copied sources: 16 unique syntax spans validated. These are historical real Joern
outputs, not a fresh scanner run. Replay script: scripts/validate_csharp_locations.py.
Raw audit: work/slice79-location-audit.json. It preserves case/flow/step provenance and
uses explicit source-root containment before reading files.

Six regression tests exercise mixed direct/preceding lines, same-line and adjacent-line
repeated identifiers, multiline expressions, UTF-8 byte offsets, CRLF, comment/string
lookalikes, faraway matches, wrong source hashes, syntax/encoding failures, oversized
inputs and invalid coordinates. These tests do not establish universal source mapping.

Source input is capped at 16 KiB, requests at 256 KiB, graph nodes at 256 and syntax
traversal at 50,000 nodes. The child uses a 10-second wall timeout and 5-second CPU limit;
Linux additionally applies 512 MiB address-space limits. macOS still needs container
resource limits for deployment validation. No source execution or LLM is involved.

Application scans and qualified triage remain unchanged. Next attach bounded ASP.NET
syntax facts only through validated spans, retaining unsupported outcomes; broader
source shapes, upstream tests and restricted Linux/OCP qualification remain open.

Final checks: all 527 application tests passed (one existing duplicate-ZIP fixture warning),
plus lint, formatting and whitespace checks. No migration or user action is required.
