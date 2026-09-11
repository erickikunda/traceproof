# Slice 133 — Java/Spring SSRF discovery

Added `java-spring-url-stream-v1`: bounded public Spring GET String RequestParam
flow to the exact java.net.URL.openStream receiver. The profile carries a separate
rule ID and CWE-918 report scope and is included in automatic Java selection.
Existing rules retain their meanings. Discovery only; advisory remains unsupported.

Native restricted Linux acceptance passed six fixtures: direct and cross-file
positives, constant-destination and disconnected negatives, unrelated-class sink
negative, and a scheme-guard candidate retained for review. Counts: 1/0/1/0/0/1.
Normal intake, native analysis, source-location validation, publication, exact report
retrieval and HTML/JSON/CSV rendering were exercised with zero model calls.

No migration or published-image rebuild. No bank OCP, runtime exploitability or
portfolio recall claim. See [operator guide](../guides/java-ssrf-discovery.md).
Next: bounded JS/TS process execution, then reflected XSS, subject to native evidence.

Full regression suite: 1,057 passed, with the existing duplicate-ZIP fixture warning.
Ruff and diff whitespace checks passed; code index refreshed.
