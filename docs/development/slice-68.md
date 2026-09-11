# Slice 68 — Bounded Joern parser diagnostic observations

Added a bounded observer for Joern 4.0.625 preparation and analysis logs. It recognizes
timestamped WARN/ERROR events and SourceParser/AstCreationPass parsing-problem markers,
counts events and deduplicates affected snapshot-relative files. Unknown file references
are retained as unmapped-event counts, never guessed from basenames. ANSI formatting is
removed before matching; raw diagnostic messages/source excerpts are not copied to reports.

At most 1 MiB per stage is inspected. Reports expose unavailable/truncated states, inspected
byte count and prefix hash. Empty/unrecognized logs never imply successful parsing.
Authoritative error/warning counts and parse-completeness claims remain unknown/false.
Log text remains an observation of untrusted tool/source output, not independent proof.

The adapter collects observations on both successful and failed attempts. Experimental
adapter 4 and projection 9 expose `joern_diagnostics` in shared reports while preserving
historical reports. Existing partial/discovery-only and Joern triage-isolation semantics
remain unchanged. This does not add model calls, migration or automatic reuse.

New fixtures: wholly malformed Java and a valid cross-file vulnerability alongside a
malformed file. Local probing demonstrated exit zero despite repeated parser warnings.
The restricted Linux acceptance suite now runs nine cases and requires parser-problem
reporting for both new fixtures; the mixed case must retain its valid candidate.

Validation: 521 tests pass (one existing duplicate-ZIP warning), including repeated ANSI
warnings, missing/truncated logs, unknown-path isolation and non-authoritative semantics.
Ruff lint/format, whitespace and package build checks pass. Real Linux validation uses
the same arbitrary UID, read-only root, network-none and resource limits as Slice 67.
Artifacts are under `work/slice68-joern-linux`.

Next: early Joern C#/ASP.NET feasibility and qualification, then Rust, before further
Spring refinement. Broad parsing/semantic completeness, x86_64 and bank OCP checks remain
unqualified. This observer is not a comprehensive parser error schema.

Real restricted Linux acceptance passed all nine cases in 64.227 seconds. Both new cases
reported five warning events and one deduplicated parser-problem file, `Broken.java`.
Malformed-only: 0/1 Java files represented, zero candidates. Mixed input: 3/4 represented,
one retained candidate. Both remain partial; no authoritative parser completeness claim.

Validated image:
`sha256:d24c591e31121fd5195cb0e0657ce6d98504454f45416022a2c88ff22abb89f8`.
