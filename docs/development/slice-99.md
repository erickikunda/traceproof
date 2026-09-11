# Slice 99 — Bounded Joern Flask advisory

## Outcome

The explicit `joern-flask-review-v1` policy enables evidence review and budgeted advisory
for the `python-flask-system-v1` Joern discovery profile. It works with check-evidence,
triage, triage-attempt and the scan-run/scan-import advisory options. Default scans remain
discovery-only. No migration, external service or live provider is needed for replay tests.

The existing workflow supplies budgets, request/page limits, idempotency, provider controls,
invocation counts and exact-attempt reports. The new policy only permits source-bound
needs_review advice or abstention. It does not authorize false-positive dismissal, prove
reachability, or make a scan complete. Other Python rules/frameworks remain outside this
policy. HTTP launch schemas are unchanged; existing report retrieval/export still works.

## Evidence boundaries

A small explicit policy registry selects language, discovery profile, rule and packaged
query digest. Java retains its existing endpoint and literal-native-code checks. Flask
uses the same pinned native-output/SARIF/source integrity checks, bounded path (2–7 nodes)
and complete retained file context. Builder version 8 retains complete small Python files
(up to 40 lines) only for this Joern profile, within existing source/envelope limits.
Larger files qualify only if retained excerpts reconstruct the complete bounded context.
Missing provenance, truncated context, changed files or unsupported syntax blocks the
provider before a reservation or call.

The isolated Flask AST parser rechecks explicit request/OS imports, aliases, rebinding,
unique endpoint locations and literal-key args/form.get syntax. The source must match the
parsed call; the final native sink must match the single os.system argument, and the
claim must quote the complete call. Source/sink lookalikes and a bare argument quote do not
satisfy the endpoint contract. Guard effectiveness stays unknown; present-guard claims and
negative verdicts are unsupported by this policy.

Joern Python records generated intermediate expressions, including multiline temporary
assignments. Their native provenance and source coordinates remain checked and each node
records source_literal. Nonliteral intermediates are retained as tool observations, never
promoted to literal source or semantic proof. All retained path steps and source hashes
must agree. Passing the advisory gate checks quote, endpoint syntax and recorded-path
consistency, not execution, sanitization, business context or exploitability.

## Validation

- 696 tests passed; one existing duplicate-ZIP fixture warning. Lint, format, whitespace
  and package build checks passed.
- Unit tests cover policy isolation, generated intermediate handling, missing/changed/
  truncated evidence, foreign imports, sink argument-only quotes, negatives, budget and
  preflight stops, idempotency, CLI evidence checks and full workflow report retrieval.
- Eight native restricted Linux cases pass: vulnerable/fixed, cross-file vulnerable/fixed,
  disconnected, renamed, shadow-request and shadow-sink. Positive cases produce one
  candidate each; the five negative cases produce zero candidates.
- Twelve native scans: eight initial scans, one fixed rescan and three positive advisory
  rescans. Three deterministic replay advisories; zero live calls. Each accounts for 140
  simulated micro-USD. Repeated imports skip and do not duplicate ledger entries.
- Synthetic replies are constructed from the first scan's fixture evidence and replayed
  against a fresh attempt. This tests contracts/orchestration, not model judgment or bank
  benchmark accuracy. The scanner itself runs natively in the Linux image.

Final acceptance: work/slice99-flask-advisory-linux-final, 54.228 seconds, ARM64 image
sha256:f4b01ce4fb2e70b1f36d191788acac27c591227efb2ecf9b1dd233f56dec7eea.
Arbitrary UID/GID 0, read-only root, no network, dropped capabilities and bounded resources.
This is local Linux acceptance; ocp_qualified remains false.

The first native run exposed that Joern's sink is the argument node, not the whole call.
The gate now binds the argument to the isolated parser's full call. A full-suite regression
also caught overly broad Python context retention; the change was restricted to Joern
Flask, preserving existing CodeQL evidence expansion. Initial diagnostics remain in
work/slice99-flask-advisory-linux. The final run includes both fixes.

## Next logical work

Apply the same explicit advisory contract to the bounded JavaScript/TypeScript Express
profile, checking its own native endpoint/context eligibility with minimum positive,
fixed and misleading-input acceptance. Retain unsupported cases rather than widening
claims by analogy. C#/Go/Rust/C-family advisory, bank benchmark quality, sustained fleet
capacity and target OCP execution remain separate gates. Prefer this language breadth to
additional CLI refinement.
