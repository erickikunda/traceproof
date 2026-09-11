# C# query-binding SQL discovery (CWE-89)

`csharp-query-commandtext-v1` removes the legacy Lookup(name) naming requirement.
The repaired frontend first discovers parameter-to-CommandText assignment flows.
Each path is then mapped to exact source spans in the bounded isolated C# parser.
Publication requires a recognized query-source syntax fact overlapping the first
flow node. Missing, ambiguous or unsupported source facts withhold the whole path.

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language csharp --joern-home /path/to/joern-cli \
  --joern-repair-dir /path/to/csharp-repair \
  --joern-profile csharp-query-commandtext-v1
```

Automatic selection retains both the legacy default and new query profile as
separate attempts/reports. Existing explicit default behavior and advisory policy
are unchanged. The new rule is advisory-unsupported. scan-import accepts the same
options. Retrieve a report by ID with get-report REPO_ID --report-id REPORT_ID and
HTML, JSON, scan-csv or candidates-csv output. Reports retain CWE-89/rule identity.

The native fixture uses a renamed ASP.NET Core action Search([FromQuery] string term),
including a namespaced cross-file helper. A constant SQL-text negative, disconnected
input, foreign attribute, missing binding and guard-present case exercise the gate.
The constant-query fixture checks text flow, not successful parameter execution.

Facts are syntax only. FromQuery on a parameter does not prove an exposed route,
controller registration, access policy or runtime framework identity. The existing
parser also recognizes bounded classic HTTP GET syntax; this slice's new native
matrix specifically exercises Core FromQuery. Minimal APIs, Request.Query reads,
FromBody and general model binding are not newly qualified.

CommandText is still a property-name sink: database type identity and SQL execution
are unverified. An unrelated property with that name can yield a candidate. No
sanitizer or guard-based dismissal is added. Configured aliases, conditional source,
large files and ambiguous spans can remain unsupported. The parser retains its
16-KiB per-file limit and existing bounded import/declaration rules.

Raw graph source/flow counts precede syntax filtering and can exceed published
candidate counts. Inspect source_mapping validated_paths/unsupported_paths and the
retained per-node audit; graph discovery does not establish complete framework
coverage. Query-source filtering does not broaden the frontend's semantic precision.

No migration, model calls or repository execution. Native validation uses the
existing repaired C# Linux image plus the current wheel in scratch. Published image
inventories and bank OCP acceptance are unchanged.
