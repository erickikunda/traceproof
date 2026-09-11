# Java/Spring file-path discovery (CWE-22)

Slice 129 adds explicit Joern profile java-spring-file-path-v1. The source model selects
public GetMapping methods with String RequestParam parameters. The sink is the resolved
java.nio.file.Files.readAllBytes(java.nio.file.Path) argument. Path.of propagation and a
cross-file helper have bounded native fixtures. Existing default JDBC SQL discovery remains
unchanged; this does not run both profiles automatically.

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern --language java \
  --joern-home /path/to/joern-cli --joern-profile java-spring-file-path-v1
```

The same explicit options apply to scan-import. Normal intake must first capture the source.
Reports retain CWE-22 scope, profile identity and candidate locations in the existing
projection 15 JSON/HTML/CSV contract. Exact report retrieval does not rerun analysis.

This is discovery-only. The existing Spring SQL advisory policy does not qualify filesystem
claims. A modeled String-to-Path flow is not proof that a directory boundary can be escaped.
Access controls, containment checks, symlink behavior and runtime library identity remain
unverified. A name.contains("..") check does not cause automatic dismissal. The fixed fixture
uses a constant path, not a supposedly universal sanitizer. A similarly named method on a
different class is not a selected sink.

Other HTTP verbs/sources, Files.readString/newInputStream/write, FileInputStream, file-serving
frameworks, general Path normalization and other Java filesystem APIs are outside this
initial profile. Joern's unknown-method propagation can overapproximate flows: preserve
candidates for review and inspect evidence rather than declaring exploitability.

Native validation installs the current wheel into disposable scratch on the existing pinned
Linux image. Published image inventories are not promoted by this slice; rebuild explicitly
before relying on the new profile in a packaged deployment. Zero model/cloud calls.
