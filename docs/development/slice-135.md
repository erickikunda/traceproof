# Slice 135 — explicit HTML response discovery

Added `express-html-send-v1` for JavaScript/TypeScript CWE-79 discovery with separate
rule IDs and automatic selection. It requires request-property flow into a chained
response.type("html" or "text/html").send argument on the callback response binding.
Joern lowers the receiver to a temporary: the query links the assignment's binding
to the send receiver and checks the explicit chained source shape. Formatting or
frontend variations can miss this narrow shape; no general response modeling claim.

Native fixtures cover direct/cross-file positives, constant output, disconnected
helper, unrelated response-like object, weak guard, JSON and plain-text negatives.
Native counts passed: 1/0/1/0/0/1/0/0 for each language. Normal source-location validation,
report publication/retrieval and HTML/JSON/CSV checks are part of the validator.
No repository/browser execution or model calls; advisory remains unsupported.

Full regression suite passed: 1,059 tests, with the existing duplicate-ZIP fixture
warning. The native graph probe identified and resolved temporary-receiver lowering;
no broad send-name fallback was added. No migration or published-image promotion.
See [guide](../guides/express-html-discovery.md). Next: bounded Java deserialization.

The strengthened disconnected-source/constant-HTML negative passed in both languages;
JavaScript was rerun separately after this fixture improvement. Ruff and whitespace
checks passed.
