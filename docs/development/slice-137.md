# Slice 137 — explicitly enabled Java XML entity discovery

Added `java-spring-xml-entities-v1` (CWE-611) and automatic selection. The query links
an explicit external-general-entities=true feature call to a factory declaration,
its directly assigned builder, and request input into parse(InputSource). This is
an observed configuration/input-flow combination, not reconstructed runtime state.

Nine restricted Linux native fixtures passed: direct, constant, cross-file,
disconnected, unrelated method, length guard, disabled feature, missing feature,
unrelated factory. Counts: 1/0/1/0/0/1/0/0/0. Source-location validation, publication,
exact retrieval and HTML/JSON/CSV checks passed, with zero model calls. 36 focused
selection, pipeline and advisory tests passed. Ruff and whitespace checks passed.

Unknown/default configurations are a disclosed recall gap. Ordering, reassignment,
overrides, resolvers, external-access settings and exploitability remain unverified.
No new advisory qualification, migration, published-image rebuild or OCP acceptance.
See [operator guide](../guides/java-xml-discovery.md).

Next: Java process-execution breadth, followed by the remaining language/API gaps.
