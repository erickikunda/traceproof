# Slice 93 — Go HTTP form input to shell command discovery

## Outcome

The opt-in `go-http-shell-v1` profile extends Go discovery beyond lookup(input) fixtures.
It is available through scan-run, scan-import and joern-go-discover. No migration,
repository build, package installation or LLM key is required.

Sources use Joern's net/http.Request.FormValue/PostFormValue graph signatures. Sinks use
os/exec.Command with exactly three arguments: one of the literal shell names sh, bash,
/bin/sh or /bin/bash, literal -c, and command text. Only recorded dataflow to the third
argument produces a candidate. The rule intentionally separates command text interpreted
by a shell from an ordinary process argument; unmodeled commands are not declared safe.

The native probe established source and sink graph identities and a recorded local flow.
The profile uses the existing source-integrity, path/line validation, persisted reports,
publication/retrieval, profile-aware retry and unsupported-triage gates. A distinct rule
and query digest preserve provenance. The rule is recognized by benchmark coverage audits
without qualifying precision or recall.

## Acceptance

Nine native cases: direct vulnerable/fixed (1/0), three-package vulnerable/fixed (1/0),
disconnected input (0), renamed parameters/import aliases with PostFormValue and /bin/bash
(1), fake HTTP import (0), fake exec import (0), and printf with an ordinary argument (0).
The runner exercises CSV intake, automatic language selection, main pipeline execution,
report retrieval/publication, source endpoint coordinates and incomplete evidence gates.
It checks batch retry suppression and performs a fresh explicit fixed-input scan.

The full automated suite passes: 621 tests, with one existing duplicate-ZIP fixture warning.
Ruff and diff whitespace checks pass. All nine restricted Linux cases passed in 55.418 seconds (ten scans including rescan).
Immutable ARM64 image:
`sha256:018fc2ea888035c19b5cb618229caa056da783db9532a9c8fa8f5ac559f813af`.
Artifacts: work/slice93-go-http-linux, including validation.json, case-results.json and
shareable reports. Runtime: arbitrary UID, read-only root, disabled network, dropped
capabilities and bounded CPU/memory. No model calls occurred.

## Limits

These are command-construction candidates, not proven invocation of Run/Start/Output or
reachable HTTP routes. Graph signatures do not authenticate dependencies, runtime identity
or sanitization behavior. No attempt is made to prove the absence of other vulnerabilities.

CommandContext, other shells/flags, variable/concatenated/raw-string shell names,
additional arguments and other HTTP sources are outside acceptance. Only .go files and
go.mod metadata are copied. Builds/dependency resolution and advanced Go semantics remain
unqualified. Failed or empty scans cannot establish a clean result; published reports
remain partial and qualified triage is unsupported. Bank OCP testing remains deferred.

## Next logical work

Continue useful source-model breadth with bounded C/C++ command-line input to system
flows, keeping C++ class/template behavior and memory-safety coverage explicitly separate.
Avoid expanding this Go slice into comprehensive HTTP or process-execution semantics.
