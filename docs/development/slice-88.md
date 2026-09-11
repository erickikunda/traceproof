# Slice 88 — C/C++ durable Joern integration

Added explicit joern-c-discover and joern-cpp-discover commands with separate packaged
rule identities using the shared Joern lifecycle and c2cpg frontend. C selects .c/.h;
C++ selects .cpp/.h/.hpp. Headers are source inputs included in graph inventory and
integrity checks. Other extensions, mixed C/C++ flows, build configuration and compilation
databases remain omitted. No application build or dependency installation is requested.

Queries select lookup(input) parameters and argument 1 of calls named system. These
are bounded integration profiles, not authentication of library identity, runtime
reachability or broad memory-safety detection. The C++ fixtures exercise the common
C/C++ subset; classes, templates and virtual dispatch remain unqualified. Reports stay
partial/non-adjudicated and evidence bundles remain unsupported for qualified triage.

All ten real restricted Linux ARM64 cases passed: each language produced 1/0 candidates
for single-file vulnerable/fixed, 1/0 for three-translation-unit vulnerable/fixed with a
shared header, and 0 for disconnected input. Every retained snippet matched its reported
source line; all selected fixture sources/headers appeared in graph inventory. Durable
report retrieval/publication and incomplete-coverage gates passed. C took 24.712 seconds;
C++ took 23.450 seconds. These are fixture timings, not production capacity estimates.
An initial fixture-packaging mistake created an empty archive; corrected before the
successful runs. Initial failure artifacts are retained at work/slice88-c-linux.

Validated image: sha256:64a1bc76ae2b43e439ef589433a9345a905be960bbc401650e62b004d67f0a22.
The offline image layer uses the trusted local UBI 9 Joern base. Runtime enforced
arbitrary UID, read-only root, no network, dropped capabilities, no-new-privileges and
CPU/memory/PID/tmpfs limits. No LLM calls. Successful artifacts:
work/slice88-c-linux-final and work/slice88-cpp-linux.

566 regression tests passed (one existing duplicate-ZIP warning), including shared
success/failure lifecycle tests for C and C++. Lint, formatting, CLI help, package build
and whitespace checks passed. No migration or user action needed. Changes uncommitted.

This completes the minimum durable integration sequence for the planned languages as
bounded opt-in profiles. It does not establish broad framework/CWE coverage. Next shared
backend selection and main-pipeline orchestration, preserving discovery-only gates,
then useful query expansion and benchmark-driven improvements. Bank OCP, throughput and
broader C++/memory-safety qualification remain separate work.
