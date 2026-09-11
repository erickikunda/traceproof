# Slice 69 — Joern C#/ASP.NET feasibility gate: not passed

Added an opt-in C# probe and fixed query under scripts/joern. It runs existing Core,
classic MVC and classic Web API vulnerable/fixed fixtures plus a new three-file
controller/service/repository pair. It uses the pinned local Joern 4.0.625 macOS ARM64
installation. The source selector Lookup(name) and CommandText assignment sink are
fixture-specific, not framework discovery. No C# production backend is enabled.

| Fixture profile | Vulnerable flows | Fixed flows | Flow expectation |
|---|---:|---:|---|
| ASP.NET Core | 1 | 0 | Met |
| Classic MVC | 1 | 0 | Met |
| Classic Web API | 1 | 0 | Met |
| Three-file Core-style chain | 0 | 0 | **Failed: vulnerable flow missed** |

The probe intentionally exits nonzero for the failed expectation. This is a meaningful
scanner qualification failure, not a failing TraceProof unit-test suite.

Observed gaps in this pinned source-only configuration:
1. Core FromQuery is absent from parameter annotation nodes; HttpGet is recorded without
   its framework namespace. Existing C# syntax parsing independently retains the source
   attribute/import evidence for all three framework fixtures.
2. The cross-file calls resolve to `<unresolvedNamespace>.Find` signatures rather than
   the declared SearchService.Find / SearchRepository.Find definitions. Both source and
   sink are present, but no complete graph flow connects them. Do not synthesize a path.
3. All six returned nodes in the three single-file positives point one line before the
   source code they describe. The next line matches in this sample. This suggests a
   frontend line-origin mismatch; a universal correction is not yet qualified.

The probe preserves raw line numbers and marks mapping unverified. File hashes and
in-range line checks do not establish quote/location alignment. No candidate may enter
qualified evidence on those checks alone. Do not apply an untested +1 adjustment globally.

Artifacts: `work/slice69-csharp-final/report.json`, and `work/slice69-probe` contains graph
call inspection, independent syntax audit and line audit. Initial query compilation was
corrected before the final eight-case run. Final rule hash:
`2d781576aa41acf1a0c6a59e8c6917da1e58ff25a0628665173761b881cb734f`.

Validation: real eight-case probe completed with seven flow expectations met and one
failed. Framework/line qualification remains failed regardless of that count. Existing
521 tests, Ruff lint/format, whitespace checks and package build pass. No migration,
LLM call, bank data or system tool replacement. This C# probe has not run under Linux
restrictions; Java-only image success must not be generalized to the C# frontend.

Next: investigate C# call resolution and coordinate conversion against pinned frontend
behavior, test source-hash/location joins to existing syntax facts, and retain these cases
as hard regressions. Do not register C# until the declared profile meets its acceptance
criteria. Rust remains the next independent engine-choice gate. If cross-file capability
cannot be restored reliably, record C# as a backend gap and evaluate alternatives; do not
hide the loss with LLM inference or present Opengrep intrafile coverage as equivalent.

No user permission or bank credential is needed to continue the investigation. These
are engine capability gaps found early, not an external access blocker.
