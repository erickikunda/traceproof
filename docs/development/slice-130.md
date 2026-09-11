# Slice 130 — Flask request-to-URL SSRF candidates

Adds python-flask-ssrf-v1 / traceproof/joern-python-flask-ssrf-v1, CWE-918. Reuses isolated
Flask source modeling and versioned native flow contracts. Adds top-level requests import/
alias validation and conservative get URL endpoint selection; local-module/rebinding
checks prevent obvious client lookalikes. Existing command and file-path modes remain
separate. No SSRF advisory policy or automatic suppression is introduced.

Fixtures: direct vulnerable, constant URL fixed, cross-file helper, disconnected source/sink,
foreign import and scheme-only guard. Expected native counts: 1/0/1/0/0/1. All reports retain
incomplete coverage and unverified destination/redirect/DNS/egress facts. No source HTTP
execution, live models, cloud calls, database migration or image promotion.

Focused source-selector/advisory/workflow regressions: 56 passed. Native runner uses
arbitrary UID, read-only root, dropped capabilities, network none and bounded resources
with a current wheel in disposable scratch. Retained results: work/slice130-reports and
work/slice130-native.log. Prior full application suite remains the baseline; no report
schema changes in this slice. Next SQL injection breadth (Slice 131).

All six native cases passed with expected counts, exact report retrieval and CWE/profile
export checks.
