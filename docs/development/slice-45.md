# Slice 45: initial C# source-only scan path

Adds csharp to explicit and automatic single-language selection. The source-only
adapter extracts a verified copy of .cs files while omitting project/solution files,
MSBuild targets, binaries and Razor views. Relative paths and hashes remain anchored
to the original snapshot. Extraction, query execution and exact report retrieval use
the existing pipeline; C# cannot inherit Python/Java indexing or completion gates.

## Explicit execution boundary

```sh
traceproof scan-run RUN_ID CSHARP_QUERY_PATH --language csharp --allow-csharp-downloads
```

CodeQL's C# none mode may provision a .NET SDK and access NuGet. The local probes
observed an attempt-local .NET 10.0.100 SDK installation and NuGet feed discovery.
No standalone dotnet was initially on PATH. Therefore C# extraction requires an
explicit allow-csharp-downloads flag, also available on codeql-extract and scan-import.
Without it, extraction stops before creating attempt artifacts. Auto selection does
not bypass this requirement. The flag permits extractor-managed downloads; it is not
an approved mirror configuration or OS network sandbox. Bank SDK/feed provisioning,
cache reuse and resource/capacity qualification remain required. Existing source-copy
and timeout/resource controls are retained. No repository build files are supplied.

## Coverage boundary

C# reports remain incomplete with csharp_semantic_index_not_qualified. Syntax indexing,
C# LLM evidence policies, Razor/generated sources, project dependency resolution,
ASP.NET Core and classic ASP.NET are not qualified. No false-positive suppression or
vulnerability confirmation is introduced. The Java-specific profile flag is not used
for C#; its initial adapter is csharp-source-only-v1.

A real classic System.Web/SqlClient vulnerable fixture produced zero candidates where
one was expected. The qualification script exits nonzero and the known miss is retained,
not relabeled as a successful clean scan. Its cause still needs dependency/model analysis.
The standard-library fixture uses modeled TcpClient.GetStream input and DbCommand
SQL construction, paired with a parameterized counterpart, to qualify the basic path
separately from ASP.NET dependencies.

## Validation tools

```sh
uv run python scripts/validate_csharp.py CSHARP_QUERY_PATH NEW_OUTPUT_DIRECTORY --auto-language
uv run python scripts/validate_csharp_classic.py CSHARP_QUERY_PATH NEW_OUTPUT_DIRECTORY
```

Both scripts explicitly allow extractor-managed downloads for synthetic fixtures.
The query is the installed codeql/csharp-queries 1.9.3 Security Features/CWE-089/SqlInjection.ql
(cs/sql-injection, path-problem). Outputs include isolated state, original SARIF and
JSON/HTML reports. No analyzed source or live model is executed by the fixture runner.
CodeQL itself runs its extraction/dependency tooling as disclosed above.

Unit tests cover C# auto-selection, omitted inputs, no inherited Python readiness,
exact report retrieval and download opt-in enforcement. No database migration.

Next: resolve classic ASP.NET qualification, establish C# syntax/evidence support and
qualify ASP.NET Core separately. L2 remains partial; neither framework is complete.

GitHub describes the C# dependency behavior in its
[compiled-language build options](https://docs.github.com/en/enterprise-cloud%40latest/code-security/reference/code-scanning/codeql/build-options-for-compiled-languages).

Validation completed: TCP/DbCommand vulnerable and fixed cases passed (1/0 candidates),
with a ready retained-flow bundle. 405 regression tests, lint, formatting and package
build passed. Classic ASP.NET remains a recorded failed qualification.
