# Slice 91 — Flask request-to-shell discovery

Added the opt-in python-flask-system-v1 Joern profile through scan-run/scan-import
(--joern-profile) and joern-python-discover (--discovery-profile). Default profiles remain
unchanged. The new rule selects single-line Flask request.args/form.get(string-key)
inputs and os.system argument flows without requiring fixture function/parameter names.

A bounded isolated AST parser selects endpoints from single top-level imports, supporting
aliases and rejecting obvious rebinding, conflicting/wildcard imports and local Flask/os
module shadows. It never imports scanned code. CPU/time/memory/source/node limits bound
parsing; unsupported files retain explicit status counts. Endpoints are joined to unique
same-name Joern calls at exact relative/absolute source file and line. Ambiguous joins are
withheld. Hashes bind endpoint selection and source; the endpoint artifact is rechecked
before publication. Raw synthetic intermediate nodes remain visible without claiming
exact source-snippet equivalence.

Published JSON projection 11 includes discovery_profile and endpoint_audit status counts
and digest. Full endpoints.json remains with the scan. Retry suppression distinguishes
profiles, including legacy default attempts. The new rule is accepted for evaluator
coverage audits; this does not promote it to qualified triage or recall measurement.

Restricted Linux ARM64 acceptance passed eight cases: direct vulnerable/fixed 1/0,
three-file vulnerable/fixed 1/0, renamed/aliased source 1, shadow-request 0, shadow-os 0,
disconnected flow 0. Main batch publication/skipping and a direct rescan were exercised
(nine scans total). Endpoint source-line checks passed; all reports remain incomplete.
Elapsed 42.418 seconds, a fixture timing rather than production throughput.
Image: sha256:328bee35f9ec5a8e4c644e3bc6ab9e06ea0eda5fb513e866cc02a952eaafa08b.
Artifacts: work/slice91-flask-linux. No model calls or application execution.

607 regression tests passed (one existing duplicate-ZIP warning); an added profile-skip
assertion then passed all 18 routing tests. Endpoint tests cover aliases, form input,
shadowed imports, rebinding, wildcard imports and unsupported syntax/access shapes.
Lint, formatting, package build and whitespace checks pass. No migration or user action
needed. Changes remain uncommitted.

Limits: syntax/import checks do not authenticate installed module identity or establish
HTTP/runtime reachability. Dynamic monkeypatching, multiline accesses, get defaults or
dynamic keys, subprocess APIs and other Flask inputs remain outside this profile.
Discovery remains partial/non-adjudicated. Next prioritize a useful JavaScript/TypeScript
HTTP-input profile rather than further local Flask refinement; broader evaluation,
benchmark ground truth, throughput and bank OCP remain separate gates.
