# Java/Spring SSRF discovery (CWE-918)

Profile `java-spring-url-stream-v1` selects public Spring `GetMapping` methods with
String `RequestParam` parameters, and flows into the receiver of the resolved
`java.net.URL.openStream(): java.io.InputStream` call. URL construction and a
cross-file helper are covered by bounded native fixtures. Automatic Joern selection
includes this profile alongside Java SQL and file-path checks.

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern --language java \
  --joern-home /path/to/joern-cli --joern-profile java-spring-url-stream-v1
```

The same options apply to `scan-import`. Intake must first capture the source.
Each attempt publishes its own report with CWE-918 scope, profile identity and
candidate source locations. Use `get-report REPO_ID --report-id REPORT_ID --format html`
for a readable report, or `json`, `scan-csv` and `candidates-csv` for integration.

These are discovery-only SSRF candidates. The Spring SQL advisory policy does not
qualify them. No network request or repository code is executed by TraceProof.
URL control does not prove access to forbidden destinations. Redirects, DNS,
protocol handlers, destination allowlists, credentials, deployment egress and
runtime reachability remain unverified. A startsWith("https://") guard does not
suppress a candidate. The negative fixture uses a constant destination, not a
claimed universal sanitizer. A different class's openStream method is excluded.

Other HTTP source bindings, URL.openConnection, HttpClient, RestTemplate, WebClient,
third-party clients and arbitrary URL transformation patterns remain outside this
profile. Unknown-method flow semantics may overapproximate propagation; inspect
retained source evidence. Zero candidates never means the repository is clean.

Native acceptance installs the wheel in disposable scratch on the pinned Linux
image with no network, an arbitrary UID, read-only root and dropped capabilities.
It does not rebuild published image inventories or qualify bank OCP operation.
No model calls or cloud access are needed. No database migration is required.
