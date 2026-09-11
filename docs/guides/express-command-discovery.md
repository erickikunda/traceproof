# JavaScript/TypeScript Express command discovery (CWE-78)

Profile `express-request-exec-v1` selects Express get/post inline callback request
query/body/params field reads flowing into the first argument of the resolved
`child_process:exec` graph signature. JavaScript and TypeScript have separate rule
identities. Automatic selection runs this profile alongside Express eval discovery.

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language javascript --joern-home /path/to/joern-cli \
  --joern-profile express-request-exec-v1
```

Use `--language typescript` for TypeScript or omit language/profile for automatic
selection. The same options apply to scan-import. Each profile publishes a separate
report; use its report ID with get-report and HTML, JSON, scan-csv or candidates-csv.

The first bounded fixture shape uses `import { exec } from "child_process"`.
This is discovery-only: a modeled request-to-command flow does not prove route
exposure, runtime package identity or exploitability. Existing eval advisory policies
do not qualify command-execution candidates. No repository code is executed, and
no LLM calls are needed. Guards remain unverified and do not dismiss candidates.

This profile does not select spawn, execFile or execSync. Constant command text is
a negative even when request data exists elsewhere. Shell options on other APIs,
CommonJS/namespace/import alias variations, routers, middleware, named callbacks,
computed request fields, JSX/TSX and arbitrary module behavior are not qualified by
this slice. Graph signature resolution is not runtime binding authentication.
Zero candidates does not mean a clean repository.

No migration. Native acceptance uses the current wheel in disposable scratch on the
pinned restricted Linux image; published image inventories are not rebuilt. Bank
OCP, benchmark precision/recall and production throughput remain separate gates.
