# Slice 76 — Opengrep C# comparison: replacement gate not passed

Recommendation: do not replace the current CodeQL C# evidence backend with either tested
Opengrep version. Stable Opengrep remains a candidate for supplementary discovery; the
interfile alpha does not recover the tested call chains. Continue the bounded Joern
resolution/source-mapping investigation, preserving CodeQL as the authorized POC reference.

## Reproducible local evidence

Downloaded official macOS ARM64 stable v1.30.0 and interfile alpha
v2.0.0-nopython-interfile.alpha.2 binaries into ignored work/opengrep. Verified both
SHA-256 values against GitHub release asset metadata; pins are in scripts/opengrep/releases.json.
No signature verification was performed. The alpha identifies itself as 1.29.0 in JSON;
release tag plus verified binary hash distinguishes it from an ordinary 1.29.0 build.

Both versions used the same local taint rule: the Lookup parameter named name is a
source; CommandText assignment RHS is a sink. Stable used --taint-intrafile; alpha used
--taint-interfile. Both requested dataflow traces. No rule registry, source build, package
restore or LLM was involved. This is fixture modeling, not ASP.NET or DbCommand identity
qualification and not a general SQL-injection rule.

| Profile | Stable vulnerable/fixed findings | Alpha vulnerable/fixed findings |
|---|---:|---:|
| ASP.NET Core, single file | 1 / 0 | 1 / 0 |
| Classic MVC, single file | 1 / 0 | 1 / 0 |
| Classic Web API, single file | 1 / 0 | 1 / 0 |
| Three-file global namespace | 0 / 0 — missed positive | 0 / 0 — missed positive |
| Three-file explicit namespace | 0 / 0 — missed positive | 0 / 0 — missed positive |
| Same global-namespace classes combined into one file | 0 / 0 — missed positive | 0 / 0 — missed positive |

All expected .cs files were reported scanned, with no native errors. The alpha reported
C# in interfile_languages_used for the original cross-file positive. The combined-file
control also misses, so the observed failure cannot be attributed solely to file
boundaries. Precise C# call/argument propagation limitations need further investigation;
these samples do not prove that every C# cross-method or interfile analysis fails.

Each main run met 8/10 fixture expectations; each combined control met 1/2. The harness
intentionally exits 1 for these missed positives. Scanner exit 0 and zero diagnostics
must not be interpreted as complete vulnerability coverage.

Single-file findings include source/sink dataflow traces. Audited 24 location objects
across those six findings, including retained trace locations: start/end byte offsets
were within source bounds and matched reported start/end lines. This establishes sample
coordinate consistency, not semantic path completeness. Original source hashes matched
after scanning. No cross-file trace was returned because those findings were missed.

## Harness and limitations

Runner: scripts/validate_opengrep_csharp.py. Usage: scripts/opengrep/README.md.
Add --combined-only for the diagnostic pair. Native outputs/logs and summary reports:
work/slice76-stable, work/slice76-alpha, work/slice76-stable-combined,
work/slice76-alpha-combined. Location audit: work/slice76-location-audit.json.

An initial scan of the tests directory selected zero files due to default ignore rules.
The repeatable harness scans copied source with an empty .semgrepignore, --no-git-ignore,
and checks the expected scanned-file count. Zero-file scans never count as safe results.
Metrics/version-check suppression is requested with local rules and an allowlisted
environment; OS network isolation is not enforced. Each subprocess has a 120-second
timeout; descendant containment and total memory limits remain unqualified. No throughput
claim is made from these tiny host probes. Linux/OCP acceptance remains open.

## Decision and next step

Opengrep can be evaluated later as an additional candidate source, with engine-specific
rules and explicit limited coverage. These results do not justify reusing CodeQL's
qualified C# triage or using an LLM to invent missing interprocedural evidence. A broader
rule pack might detect other issues but does not repair this demonstrated flow gap.

Joern already retains the explicit-namespace cross-file path, giving us a narrower
observed repair target. Proceed with the bounded global-namespace call-resolution
regressions and per-node coordinate qualification from Slice 75. If that requires a
substantial custom resolver, reconsider the C# backend rather than assuming either
Opengrep release supplies parity. No production backend, schema or API changed.

Validation: real scanner comparison and location audit completed; lint, formatting and
whitespace checks passed. No user action is needed. Changes remain uncommitted.

Primary release references:
- [Stable v1.30.0](https://github.com/opengrep/opengrep/releases/tag/v1.30.0)
- [Interfile alpha, explicitly for testing](https://github.com/opengrep/opengrep/releases/tag/v2.0.0-nopython-interfile.alpha.2)
