# Slice 95 — Rust environment-to-shell discovery and POC checkpoint

## Outcome

The opt-in rust-env-shell-v1 profile removes fixture-function dependence for a bounded
Rust environment-input pattern. Main scan-run/scan-import and joern-rust-discover accept
it; defaults, the trusted toolchain requirement and strict Cargo preparation remain intact.
No migration or LLM key is required for discovery.

Sources require Joern's std::env::var graph signature and a literal key. Sinks require
standard-library Command::arg in a direct chain from a literal sh/bash or /bin/sh or
/bin/bash constructor, then literal -c, then the command text. The selector follows the
recorded receiver tree, stripping at most four address/dereference wrappers per receiver.
Joern supplies the actual source-to-argument flow; no edges are synthesized.

Distinct rule/profile/query identity and existing source-integrity, coordinate, report
retrieval/publication, retry and evidence gates are preserved. Benchmark coverage audits
recognize the CWE-78 candidate scope without qualifying precision/recall.

## Acceptance

Nine restricted Linux cases pass: direct vulnerable/fixed (1/0), cross-module
vulnerable/fixed (1/0), disconnected (0), import aliases with /bin/bash (1), source and
sink lookalikes (0 each), and ordinary non-shell arguments (0). The runner exercises CSV
intake, automatic language detection, main scanning, persisted reports, publication,
graph inventory, endpoint coordinates, retry suppression and unsupported qualified triage.
The fixed case is explicitly rescanned, for ten native scans and zero model calls.

Elapsed time: 70.873 seconds. ARM64 image:
`sha256:577bf2b3debc3cbfaf04093cefee88edb170b7fa93c0f356af7b76fa96a0d472`.
Artifacts: work/slice95-rust-env-linux, including validation.json, case-results.json,
diagnostics and shareable reports. The image layers on the previously qualified pinned
Rust UBI 10 runtime and runs with arbitrary UID, read-only root, no network, dropped
capabilities and resource limits. Actual bank OCP acceptance is still deferred.

Full automated suite: 635 passed; one existing duplicate-ZIP fixture warning. Ruff and
diff whitespace checks pass. The native macOS probe is retained in work/slice95-probe.

## Limits

Environment attacker control, actual process execution and exploitable security boundaries
are not established. Standard-library graph identity and sanitization remain unqualified.
Split builders, args arrays, command-line sources, var_os, dynamic keys, other shells and
flags, dependency-bearing Cargo projects and advanced Rust semantics remain out of scope.
Only .rs and generated strict Cargo metadata are analyzed. No repository build hooks or
new dependencies are executed/installed. Zero candidates cannot establish a clean result.
Reports remain partial/discovery-only; qualified triage and measured recall are unsupported.

## POC checkpoint and next work

The bounded language integration gate and this useful-input expansion pass are complete
for the documented profiles, not for all languages' frameworks or CWEs. C# still uses its
accepted repaired fixture profile; C/C++ memory-safety and broader Cargo support remain open.

The main functional gap is Joern-to-LLM evidence portability: joern_pipeline publishes
without model calls, and claims.requirements supports only CodeQL policy/rule pairs.
Existing LLM keys or Ollama configuration do not bypass that gate. This must not be
resolved by merely accepting a Joern rule name or treating native paths as proven flows.

Next: assess and implement one bounded Java/Spring Joern evidence-policy slice, reusing
the existing syntax/quote checks where valid, with engine-specific provenance and negative
controls. Only after its explicit evidence gates pass should an opt-in advisory path be
connected. Preserve unknown reachability and unsupported negative verdicts. Defer broad
policy promotion and further per-language model refinement until this vertical path works.

Other open gates remain: representative 50-repository quality evaluation; complete S5
comparisons and per-profile cost/coverage evidence; demonstrated multiworker/fleet capacity;
actual OCP dev deployment and enterprise image/identity/storage approvals. Synthetic fixture
timing does not establish 1,000 repositories/day. None blocks local evidence-portability work.
