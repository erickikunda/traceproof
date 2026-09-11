# Slice 101 — Bounded repaired Joern C#/ASP.NET advisory

## Outcome

The explicit joern-csharp-review-v1 policy enables check-evidence, triage, triage-attempt
and main scan/advisory integration for the default repaired Joern C# profile. The workflow
reuses run budgets, page/request limits, reservations, provider controls, idempotency,
repeat suppression and exact-attempt report publication. No migration or live provider is
required for replay validation. Default scans remain discovery-only.

This is advisory portability for the existing Lookup(name)-to-CommandText discovery query,
not broader ASP.NET discovery. Core FromQuery and bounded classic public HttpGet parameter
syntax can qualify. Passing advice remains needs_review, never a verified vulnerability or
permission to dismiss a candidate. Guard presence and negative verdicts remain unsupported.

## Evidence checks

C# normalization differs from other languages: native output contains coordinates corrected
by the existing pinned span mapper before SARIF publication. Builder version 10 replays that
mapping from hash-checked native output and source, verifies recorded mapped/unsupported
path counts, and regenerates SARIF to match the exact retained candidate. It does not trust
the source-mapping JSON artifact as authoritative evidence.

The recorded repair identity must contain the expected patched-source digest and a valid
receipt digest. The existing scanner rechecks operator repair classes/jars/source before
and after discovery; advisory records its repair identity and mapper version. Hashes are
integrity evidence, not authentication of the tooling publisher. No additional repair or
custom flow edges are introduced by this slice.

To bound repeated parsing, evidence reconstruction accepts at most 32 native paths and
128 total native nodes before invoking the mapper; larger results get native_mapping_limit
and remain candidates without advisory. The selected path must have 2–7 nodes, all literal
on their mapped source lines, with complete retained source context and matching hashes.
Existing source/envelope/parser limits still apply. This is a POC work bound, not measured
fleet throughput; repeated source mapping remains a future optimization opportunity.

Endpoint checks re-run isolated span validation with framework syntax facts. The first
native node must fall inside the recognized request-parameter fact; the last must fall
inside the CommandText right-hand-side fact. This prevents another parameter on the same
line from supplying the source claim. Claims must also quote the complete recognized
source/assignment line. A bare RHS quote is insufficient. Missing repair provenance,
ambiguous spans, truncated context, changed native data or unsupported source syntax blocks
advisory before any provider invocation.

Framework/API identity, runtime route exposure, sanitizer semantics and exploitability are
not proven. CommandText remains a syntactic sink, including potential application-defined
lookalikes. Multiline native spans and broader controllers/query shapes may remain
unsupported. The overall scan report stays partial/incomplete and unverified.

## Validation

805 automated tests pass (one existing duplicate-ZIP fixture warning); lint, format,
whitespace and package build checks pass. All ten restricted Linux cases pass in
103.312 seconds on ARM64 image
sha256:bcfc0b4a498c50e95c6c1c2b78fa77fc0c85a55e3b8572c090cf16631649944a.
Artifacts: work/slice101-csharp-advisory-linux-final. Arbitrary UID/GID 0, read-only root,
no network, dropped capabilities and bounded runtime resources were enforced.
ocp_qualified remains false; actual bank OCP execution is deferred.

The first run also passed; the final image additionally includes the mapping-work cap and
its regression tests. Initial results remain in work/slice101-csharp-advisory-linux. Unit coverage
includes Core/MVC/Web API mapped coordinates, repair identity, mapper version/counts, native
integrity, context limits, exact endpoint quotes, negative rejection, mapping work bounds,
zero-call evidence/budget stops, idempotency and main-workflow report retrieval.

Native acceptance has ten cases: vulnerable/fixed pairs for Core, classic MVC, classic Web
API and a cross-file chain, plus a foreign-framework import and an unbound Core parameter.
Four positive cases each produce one replay needs_review advisory. Both misleading-source
cases remain visible as candidates but receive incomplete_evidence/abstain with zero calls.
The four fixed cases produce zero candidates. These fixture outcomes are not recall or
precision measurements and do not establish application safety.

The runner performs sixteen native scans (ten discovery attempts and six candidate
advisory rescans), creates deterministic fixture replies from the original bundles and
replays them against fresh attempts. It verifies repeat-import suppression, exact report
retrieval and accounting: four replay calls, zero live calls, 560 simulated micro-USD in
total. No bank data or external model judgment is involved.

## Next logical work

Port the same bounded advisory contract to the existing Go HTTP-to-shell profile. Preserve
unknowns and require minimum native/source/endpoint acceptance rather than broad language
claims. Then address Rust and C-family advisory. Broader C# request discovery remains a
separate coverage enhancement. Bank benchmark quality, live-model evaluation, sustained
1,000-repository/day throughput and actual bank OCP execution remain open gates.
