# Slice 85 — JavaScript/TypeScript durable Joern integration

Added explicit joern-javascript-discover and joern-typescript-discover commands with
separate packaged rule identities and language-specific source selection. Both use the
shared Joern lifecycle and jssrc2cpg frontend, preserving Java/Python/C# behavior.
Archive intake, persistence, candidate retrieval, HTML/JSON publication and evidence
bundle gating now work for these bounded profiles.

Sources are lookup(input) parameters and sinks are first arguments of calls named eval.
Only .js or .ts files are selected per profile. Mixed-language flows, JSX/TSX, framework
models, dependencies and project configuration remain outside this scope. Call-name
matches do not authenticate builtin eval or establish HTTP/runtime reachability.
All successful scans remain partial/non-adjudicated, including zero-candidate cases;
qualified triage and automatic result reuse remain disabled for these rules.

Real restricted Linux ARM64 acceptance passed all ten cases: each language yielded
1/0 for single-file vulnerable/fixed, 1/0 for ES-module cross-file vulnerable/fixed,
and 0 for disconnected input. Every returned snippet matched its reported source line;
all selected fixture files were represented. Published reports retained incomplete
coverage and bundles remained unsupported for qualified triage.
JavaScript completed in 29.039 seconds; TypeScript in 28.784 seconds, sequentially.
These are fixture timings, not production throughput estimates.

Image: sha256:1cb3bd4aa908ec7ba68a3eaf9df6eddc5c6ba17189a3a23b3af48c8fcff57f15.
Built offline atop the trusted local Joern base. Runtime enforced arbitrary UID,
read-only root, no network, dropped capabilities, no-new-privileges and bounded
CPU/memory/PID/tmpfs resources. No LLM calls or application builds were made.
Artifacts: work/slice85-javascript-linux and work/slice85-typescript-linux.

546 tests passed (one existing duplicate-ZIP warning), including shared success/failure
lifecycle checks for both new profiles. Lint, formatting, whitespace, CLI help and
package build checks pass. No migration or user action required. Changes uncommitted.

Next Go durable integration and the same minimum acceptance checks, then Rust.
Broader detection/benchmarking and actual bank OCP validation remain separate gates.
