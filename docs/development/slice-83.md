# Slice 83 — Durable C# discovery in restricted Linux

The C# container acceptance suite now exercises archive intake, SQLite scan persistence,
retrieval, HTML/JSON publication and evidence-bundle gating for the opt-in repaired
Joern profile. Two durable cases extend the existing twenty flow/binding cases.
The published mapping counts must match the expected paths with none unsupported.
Reports remain incomplete, and qualified Joern triage remains unsupported.

Validation passed all 22 cases in 133.774 seconds on Linux ARM64, including
18 source spans and seven source/five sink syntax fact attachments. The durable
vulnerable/fixed pair yielded 1/0 candidates. The image was built without network access;
runtime used arbitrary UID, read-only root, no network, dropped capabilities,
no-new-privileges, 2 CPUs and 4 GiB memory with PID/tmpfs limits. No LLM calls were made.
Image: `sha256:f7ce91d88aff76b0b452fa9eba2ae4b1ebf23bb6716a607c9a5f00ad36370f7b`.
Local artifacts: work/slice83-csharp-linux, including durable HTML/JSON reports.

All 537 regression tests passed (one existing duplicate-ZIP warning); lint, formatting,
package build and whitespace checks passed. No migration or user action is needed.
Changes remain uncommitted.

This qualifies the bounded local integration, not full C# coverage or bank OCP.
The Lookup(name)/CommandText selector remains fixture-specific. Next qualify a bounded
ASP.NET HTTP source profile with renamed actions/parameters and negative controls,
before expanding the packaged query. API identity, broader rules, upstream repair
packaging, throughput, PostgreSQL deployment and actual OCP remain separate gates.
