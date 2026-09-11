# Slice 134 — Express command-execution breadth

Added explicit `express-request-exec-v1` discovery for JavaScript and TypeScript.
The query reuses the existing Express request-property source model and selects
resolved child_process:exec first-argument flow. Separate rule IDs and CWE-78 scope
persist in reports. Automatic selection includes the new profile alongside eval.
Existing eval rules are unchanged; advisory remains unsupported for the new rules.

Fixtures exercise direct and cross-file positives, constant-command and disconnected
negatives, a local exec shadow, a weak guard retained as a candidate, and execFile
with request data in an argument array excluded from this profile. The validator
uses normal intake, native Joern, source-location validation, publication and exact
report retrieval with HTML/JSON/CSV CWE checks. No repository execution/model calls.

Regression: 36 focused selection, pipeline and advisory tests passed. Restricted
Linux native acceptance runs seven cases per language, counts 1/0/1/0/0/1/0.
No database migration or published-image promotion. The profile is discovery-only,
not proof of exploitability or complete framework coverage.

See [operator guide](../guides/express-command-discovery.md). Next: bounded reflected
XSS discovery, with output-context negatives rather than generic string-flow claims.
