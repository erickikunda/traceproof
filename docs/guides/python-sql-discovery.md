# Python/Flask SQL-text discovery (CWE-89)

Slice 131 adds python-flask-sql-v1 for a bounded SQLite DB-API shape:
Flask request.args/form.get input reaching SQL text in
sqlite3.connect(LITERAL_DATABASE).execute(QUERY[, PARAMETERS]). The source code is parsed,
never imported or executed; no database is opened by the scanner.

```sh
veriflow --state-dir /path/to/state scan-run RUN_ID --engine joern --language python \
  --joern-home /path/to/joern-cli --joern-profile python-flask-sql-v1
```

Normal source intake must create RUN_ID first; scan-import accepts the same explicit
profile. Query argument 1 is the sink, not the bound parameter collection in argument 2.
The native fixed fixture uses a constant parameterized query and produces no candidate.
Dynamic SQL concatenation remains a candidate. Length checks do not establish safe SQL.

Only single-line positional execute calls on an immediately imported sqlite3.connect with
one literal database argument are qualified. Import aliases are supported conservatively;
foreign/rebound modules are withheld. Connection/cursor variables, factories, connection
pools, psycopg/Oracle/ODBC drivers and ORMs remain unsupported. This is a narrow initial
DB-API profile, not general Python SQL coverage. No SQL grammar or sanitizer proof is added.

Projection 15 reports retain CWE-89, rule/profile identity and source locations. Advice is
unsupported for this new rule; existing Java/C# SQL policies are not reusable by assumption.
Default profiles and automatic profile selection are unchanged in this slice. The latter
is the next planned feature. Published images require an explicit rebuild for this profile;
local validation installs the new wheel into disposable scratch on a pinned toolchain.
