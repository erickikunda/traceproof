# Slice 89 — Joern in the main scan workflow

scan-run and scan-import now accept --engine joern, --joern-home, optional
--joern-repair-dir and --rust-home. The positional query argument is optional for Joern
and remains required for default CodeQL. Joern accepts only its packaged profiles;
CodeQL query/preparation options and unsupported resource overrides are rejected.
Existing standalone discovery commands remain available.

The main workflow routes to the durable Joern lifecycle rather than pretending a CPG is
a CodeQL prepared database. The lower-level prepared-database API/registry remains
CodeQL-specific. No new API scan-launch endpoint was added; report retrieval is unchanged.
Preparation and query timeouts are honored separately, and publication pins the exact
attempt. Even failed discovery attempts yield explicitly incomplete reports. Model calls
remain zero and Joern evidence is not promoted to qualified triage.

--language auto selects one detected supported language among Python, Java, C#,
JavaScript, TypeScript, Go, Rust, C and C++. Mixed-language inputs require explicit
selection. Headers alone do not select C/C++. Existing profile extension/admission limits
remain in force. Tool paths needed only by C#/Rust can be supplied for a mixed import;
each individual row passes only the relevant path to its selected profile.

Batch pagination, pause/cancel and row-error behavior remain intact. Default skipping
checks only prior Joern attempts for the same run/language, including failures; prior
CodeQL attempts do not suppress Joern. This is local retry suppression, not freshness
verification or a new result reuse guarantee. --rescan is required after failures or
tool/profile changes. Direct scan-run creates a new attempt. Concurrent distributed
exactly-once dispatch remains outside this sequential local workflow.

584 regression tests passed (one existing duplicate-ZIP warning). New tests cover all
nine language selections, mixed-language rejection, incompatible options, CodeQL/Joern
attempt separation, failed/successful publication, retry skipping and separate timeouts.
Existing CodeQL CLI/batch tests pass. Lint, formatting, package build and whitespace pass.

Real restricted Linux acceptance passed five Python fixture cases through scan-import,
with repeated calls skipped and an extra direct fixed-case rescan producing a new
attempt: six scanner executions total, zero LLM calls. Expected 1/0 single-file and
cross-file pairs plus disconnected 0 remained incomplete. Runtime checks passed under
arbitrary UID/read-only root/no network and the existing resource restrictions.
Elapsed: 26.041 seconds; not a production capacity estimate.
Image: sha256:a9a2cc5f8d7afcff9fa79dd76895816da04e1fa2562d2cbfcdce251a7c79c667.
Artifacts: work/slice89-pipeline-linux. No migration or user action needed; uncommitted.

Next verify the existing benchmark/evaluation workflow against these Joern results and
make detection coverage gaps visible across languages. Use synthetic data locally until
the 50-repository ground-truth corpus is available. Broader query/framework coverage,
qualified triage, capacity and bank OCP remain open; orchestration completion does not
establish CodeQL-equivalent detection coverage.
