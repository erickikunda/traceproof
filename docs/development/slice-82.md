# Slice 82 — Durable experimental repaired C# discovery

Added the opt-in joern-csharp-discover command. It reuses the durable Joern scan lifecycle
with a separate packaged rule/profile, copies only verified .cs files, runs the repaired
frontend and fixed query, validates source spans, and normalizes publishable paths into
SARIF candidates. Java remains the default of the existing API/command and keeps its
rule identity. No automatic pipeline/backend selection is changed.

The initial C# profile is deliberately Lookup(name) to CommandText assignment RHS,
matching the assessed query shape. It is not broad ASP.NET vulnerability discovery.
Syntax framework facts are retained in an audit artifact but do not authenticate source
or sink API identities. Successful scans always remain partial/non-adjudicated, including
zero candidates; no CodeQL policy is inherited and qualified Joern triage stays unsupported.

The operator supplies the trusted Joern home and isolated repair-build directory. The
adapter reconstructs its classpath from the build receipt, checks the known patched
source hash and recorded class/jar hashes, and repeats integrity checks after execution.
Repair builds under scan artifacts are rejected. Receipts detect modification, not tool
publisher authenticity; a trusted tooling supply chain is still required. Per-scan
rehashing is intentionally conservative and remains a scaling optimization opportunity.

Every node in a published path must map to a unique source span. Whole paths with
unsupported/ambiguous mapping are withheld, not silently shortened. Native flows remain
retained alongside source-mapping.json; validated/unsupported path counts appear in scan
reports and published JSON (projection version 10). Native modeled-flow coverage remains
separate from the number of mapped/published candidates. Hash and source/query integrity
checks preserve the existing lifecycle guarantees. This command alone does not provide
OS network isolation.

Validation: a real global-namespace three-file vulnerable/fixed pair ran through archive
intake, scan persistence, retrieval, report publication and bundle creation, yielding
1/0 candidates. Both reports remained incomplete; bundle engine/rule policy stayed
unsupported for qualified triage. Artifacts: work/slice82-durable. Repeatable probe:
scripts/validate_joern_csharp_discovery.py. The operator guide documents CLI use.

Four tests cover durable C# reporting, withheld ambiguous paths, invalid references and
missing repair tooling; existing Java tests pass. Full suite: 537 passed (one existing
ZIP warning). Lint, formatting, whitespace and package build checks pass.

Next extend restricted Linux acceptance to this durable command/report path. Slice 81
qualified the underlying C# scanners and mapping/facts in Linux; the new integration was
validated on macOS this slice, not yet requalified inside that container. Broader C#
rules, upstream patch review/packaging, throughput and actual bank OCP remain open.
No migration or user action is required. Changes remain uncommitted.
