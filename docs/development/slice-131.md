# Slice 131 — Python SQL-text breadth

Adds python-flask-sql-v1 / traceproof/joern-python-flask-sql-v1, CWE-89, using the bounded
sqlite3.connect(literal).execute(query[, parameters]) shape. The flow sink is SQL text,
never the parameter collection. Isolated import/binding selection reuses existing Flask
sources without weakening command/path/SSRF profiles. Cursor variables/other drivers are
not supported by this slice. No SQL advisory or sanitizer verdict is introduced.

Six native fixtures: concatenated query, constant parameterized query, cross-file helper,
disconnected source/sink, foreign module and weak length guard. Expected counts 1/0/1/0/0/1.
Reports persist CWE/profile fields and remain incomplete. Runtime uses existing pinned
Linux toolchain with a new wheel in private scratch, arbitrary UID, read-only root,
network none, dropped capabilities and bounded resources. No source SQL is executed.

Focused parser/advisory/workflow regressions: 60 passed. Native evidence is retained in
work/slice131-reports/validation.json. No cloud/model calls, migration or image promotion.
Next Slice 132: deterministic language/profile selection, including honest mixed-language
handling and explicit overrides; no LLM required for routine applicability decisions.

All six native cases passed, including the bound-value negative and retained report exports.
