# C# query-to-shell discovery (CWE-78)

`csharp-query-shell-start-v1` discovers mapped query-binding input flowing into the
argument string of fully qualified System.Diagnostics.Process.Start(executable, args).
It requires a literal sh, /bin/sh, bash or /bin/bash executable and an argument
expression whose written code begins with the ordinary string literal prefix "-c ".
The initial fixture uses a quoted command concatenation:

```csharp
System.Diagnostics.Process.Start("/bin/sh", "-c \"" + input + "\"");
```

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language csharp --joern-home /path/to/joern-cli \
  --joern-repair-dir /path/to/csharp-repair \
  --joern-profile csharp-query-shell-start-v1
```

Automatic selection includes the new profile with existing C# SQL/file profiles,
as separate attempts and reports. scan-import accepts the same options. Use the
report ID with get-report REPO_ID --report-id REPORT_ID --format html, json,
scan-csv or candidates-csv. Reports retain CWE-78 and rule identity.

Matching is syntax-based, not authenticated .NET binding. Source-defined types
named System, Diagnostics or Process conservatively exclude this profile, possibly
omitting unrelated legitimate calls. Imported short names and other receiver forms
are outside this profile. The exact source-span/query-fact gate remains mandatory.

Findings are candidates. Argument-string splitting, escaping, command versus later
shell positional data, executable identity, route exposure and runtime exploitation
are unverified. A length guard does not dismiss a flow. Constant arguments, unrelated
executables, missing -c prefix, unrelated Start methods, a local Process type and
unbound input are negatives, without declaring those applications safe.

ProcessStartInfo, ArgumentList, instance Start, UseShellExecute configurations,
Windows shells, variable executables, interpolated/verbatim strings and other
shell flags remain gaps. Cross-file string propagation is included in a bounded
Core FromQuery fixture. Existing SQL advisory policies do not qualify these findings;
the new rule remains advisory-unsupported.

No processes or repository code are executed during scanning. No model calls or
migration. Restricted Linux acceptance installs the wheel in scratch on the repaired
C# image; published image inventories and bank OCP acceptance are unchanged.
