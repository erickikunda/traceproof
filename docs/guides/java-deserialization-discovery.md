# Java/Spring object deserialization discovery (CWE-502)

`java-spring-object-read-v1` selects public Spring GetMapping methods with String
RequestParam input flowing into the receiver of the exact resolved
`java.io.ObjectInputStream.readObject(): java.lang.Object` call. The initial flow
shape is Base64 decoding into ByteArrayInputStream, then ObjectInputStream and
readObject. A cross-file helper is included in native fixture validation.

```sh
veriflow --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language java --joern-home /path/to/joern-cli \
  --joern-profile java-spring-object-read-v1
```

Automatic Joern selection includes this profile with the Java SQL, file-path and
SSRF checks, each with its own attempt and report. scan-import accepts the same
options. Retrieve the exact report with get-report REPO_ID --report-id REPORT_ID
--format html, json, scan-csv or candidates-csv. CWE-502 scope and rule identity
are retained even when there are no candidates.

This is discovery-only. Filters, allowlisted classes, stream validity, available
gadget classes, deployment configuration and runtime reachability remain unverified.
A byte-length guard does not suppress a candidate. Existing Spring SQL advisory
policies cannot qualify this rule. A configured object filter might make a reported
path non-exploitable; this profile does not prove either filter adequacy or bypass.
No serialized objects or repository code are executed during scanning.

The constant-input fixture uses a fixed serialized-null value. An unrelated class's
readObject and construction without readObject are negatives for this detector,
not declarations that those applications are safe. Other HTTP bindings, raw byte
request bodies, readUnshared, other serializers, subclass overrides and arbitrary
stream transformations remain outside the qualified fixture scope. Joern's external
method propagation may overapproximate data flow; inspect retained source evidence.

No model calls or migration. Native acceptance installs the wheel in restricted
Linux scratch without rebuilding published image inventories. Bank OCP, benchmark
precision/recall and production throughput remain separate acceptance gates.
