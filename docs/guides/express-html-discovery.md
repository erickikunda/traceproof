# Express explicit-HTML response discovery (CWE-79)

`express-html-send-v1` discovers bounded JavaScript/TypeScript request-property flow
to `response.type("html").send(...)` or `response.type("text/html").send(...)`.
The response receiver must resolve to the second parameter of a recognized Express
get/post inline callback. Sources use the existing first-parameter query/body/params
field model. The explicit content type provides HTML context; a generic send call
is not enough for this profile.

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language javascript --joern-home /path/to/joern-cli \
  --joern-profile express-html-send-v1
```

Use typescript for TS. Automatic selection includes this profile alongside eval and
exec as separate attempts/reports. scan-import accepts the same options. Retrieve
an exact report with get-report REPO_ID --report-id REPORT_ID --format html, or
JSON/scan-csv/candidates-csv for integration. Reports retain CWE-79 and rule identity.

These are reflected-XSS candidates, not browser execution proofs. Encoding, object
versus string runtime types, response mutations, middleware, CSP and runtime route
exposure remain unverified. Existing eval/command advisory policies do not qualify
this rule. A short-length guard does not suppress a candidate. JSON and explicit
text/plain are excluded from this detector, without declaring the application safe.

The bounded form requires the directly chained type(...).send(...) call on the
callback response parameter. Separate header setters, aliases, response helpers,
nonliteral MIME types, templates, res.write/end, default send content types, routers,
named callbacks, computed properties and JSX/TSX remain gaps. Cross-file string
helper propagation is modeled; arbitrary escaping helpers are not certified.
Graph bindings do not authenticate runtime framework identity.

No repository code/browser execution or LLM calls. No migration. Restricted Linux
validation installs the wheel in scratch; published container inventories and bank
OCP acceptance are unchanged. Zero candidates is never a clean verdict.
