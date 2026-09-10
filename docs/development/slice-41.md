# Slice 41: narrow Java SQL advisory evidence policy

Gate version 4 enables java/sql-injection advisory review using explicit Spring
RequestParam syntax and JDBC executeQuery syntax anchored to retained CodeQL flows.
Other Java rules, sources and sink forms remain unsupported.

The source and sink claims require complete bounded Java file context, valid parser
syntax, exact quoted lines and matching retained flow endpoints. Foreign imports,
unresolved wildcard imports and same-file RequestParam declaration lookalikes fail.
The retained thread must include all steps. This does not prove Java symbol binding,
Spring runtime registration, taint semantics or exploitability.

Guard effectiveness may remain unknown for needs_review. No Java guard/counterevidence
syntax is qualified, so likely_false_positive advice cannot pass. Candidates are never
automatically removed. Existing model configuration, classification and budget gates
still apply; this change makes the one Java rule eligible for those existing workflows.

Bundle builder 4 retains complete Java files up to 40 lines, within existing cumulative
16 KiB source and 32 KiB envelope limits. Larger or incomplete snippets fail the Java
policy conservatively. Existing immutable bundles/reports are unchanged. New bundles
have new identities. Gate version participates in triage request identity; old keys
may conflict. Use an explicit local check-evidence for rechecking; do not rotate keys
just to retry an uncertain provider call. No migration or live model calls required.

Validation includes the real retained Spring fixture path, plus tests for foreign
imports, local lookalikes, fragment context, comment lookalikes, disconnected flow
and negative suggestions. validate_spring.py now also checks a synthetic advisory
decision locally without a provider call. Java static readiness remains incomplete.

Next: broader Java source/sink and guard qualification, then separately qualified
Spring Maven/Gradle build profiles. L1 remains partial; no corpus quality credit.
