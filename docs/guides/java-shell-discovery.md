# Java/Spring shell command discovery (CWE-78)

`java-spring-runtime-shell-v1` selects public Spring GetMapping String RequestParam
flow into the third element of an inline Runtime.exec(String[]) array containing
exactly three elements: literal sh, /bin/sh, bash or /bin/bash; literal -c; and command
text. The sink must resolve to java.lang.Runtime.exec(String[]).

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language java --joern-home /path/to/joern-cli \
  --joern-profile java-spring-runtime-shell-v1
```

Automatic Joern selection includes this profile with the other Java checks, each
with a separate attempt/report. scan-import accepts the same options. Use the
returned report ID with get-report REPO_ID --report-id REPORT_ID --format html;
JSON/scan-csv/candidates-csv provide machine-readable output with CWE-78 scope.

The initial source shape is:

```java
Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", input});
```

Findings are command-injection candidates, not exploitability proofs. A length guard
does not dismiss them. Shell executable identity, route exposure, environment and
runtime controls remain unverified. Existing Spring SQL advisory policies do not
qualify this rule. No repository code or process is executed during scanning.

Constant command text, unrelated exec methods and ordinary executable arguments
are negative fixtures. An extra positional argument after fixed shell command text
is excluded from this exactly-three-element profile. These exclusions do not imply
that general argument injection or other shell patterns are safe.

Array variables, other Runtime.exec overloads, ProcessBuilder, Windows shells,
alternative flags, additional array elements, nonliteral executable names, other
HTTP bindings and arbitrary wrappers remain outside this fixture scope. Cross-file
command-text helpers are supported by a bounded native fixture. Modeled data flow
may overapproximate unknown methods; inspect retained evidence.

No model calls or migration. Restricted Linux validation installs the wheel in
scratch; published container inventories and bank OCP acceptance are unchanged.
