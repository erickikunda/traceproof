# C# query-to-file-path discovery (CWE-22)

`csharp-query-file-read-v1` discovers mapped query-binding input flowing into the
path argument of fully qualified `System.IO.File.ReadAllText(path)` syntax. It uses
the existing repaired frontend and source-span/query-fact gate. Action and parameter
names are unrestricted within those syntax checks.

```sh
veriflow --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language csharp --joern-home /path/to/joern-cli \
  --joern-repair-dir /path/to/csharp-repair \
  --joern-profile csharp-query-file-read-v1
```

Automatic selection includes this profile alongside legacy and query-binding SQL,
each with separate attempts/reports. scan-import accepts the same options. Retrieve
an exact report with get-report REPO_ID --report-id REPORT_ID --format html, json,
scan-csv or candidates-csv. CWE-22 and rule identity remain explicit.

The frontend leaves the .NET API signature unresolved. This profile therefore
requires exactly the written receiver System.IO.File and one path argument; it is
not a symbol-binding proof. If the graph contains a source-defined type named System,
IO or File, this entire profile selects no sinks to avoid obvious lookalikes. This
conservative exclusion can miss unrelated legitimate file reads. Zero results never
mean a clean repository. Imported short-name File calls are outside this profile.

Published candidates require a recognized query-source fact at the first mapped
flow node. Native examples use Core FromQuery, including a namespaced cross-file
helper. Existing parser limits, unsupported imports and ambiguity rules apply.

A flow does not prove escape from an intended directory. Containment, symlinks,
permissions, route exposure, runtime API identity and file access are unverified.
A Contains("..") guard does not suppress a candidate. Constant paths, unrelated
ReadAllText methods, a source-defined System.IO.File, unbound input and disconnected
helpers are negatives for this detector. Existing SQL advisory policies do not
qualify file-path claims; this new rule remains advisory-unsupported.

Other file APIs, overloads, aliases, request bindings and arbitrary path transformations
remain gaps. No file in the target application is opened by the scanner; source code
is analyzed without executing it. No model calls or migration. Native acceptance
installs the wheel into scratch on the repaired C# Linux image; published images
and bank OCP acceptance are unchanged.
