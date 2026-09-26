# Slice 46: pinned C# SDK/reference profiles and classic ASP.NET diagnosis

The classic fixture miss is diagnosed: CodeQL recorded the request and connection
parameters as unknown types before supplying references. With the pinned profile it
resolves HttpRequest and SqlConnection, produces one SQL-injection candidate for the
vulnerable fixture and zero for its parameterized counterpart. This qualifies that
fixture, not broad classic ASP.NET coverage.

## Implemented dependency profile

`--csharp-dependency-profile PATH` is available on extraction, scan-run and scan-import.
A versioned JSON manifest pins every regular file under SDK and reference directories
with SHA-256 hashes. Paths must stay beneath the profile directory; symlink inventory
entries, missing/extra files and mismatched bytes are rejected. Maximum manifest size
is 4 MiB and each inventory is capped at 20,000 files. Pinning records observed bytes;
it does not certify upstream provenance. Operators must approve the supplied artifacts.

The extractor receives an explicit DOTNET_ROOT/PATH, a trusted generated NuGet.Config,
a local fallback feed, disabled feed responsiveness probes and explicit framework
reference paths. Writable package/cache/home state is per-attempt. CodeQL and observed
SDK versions must match the profile. Inputs are reverified after extraction. Reports
retain profile ID, versions and file count, not the full SDK inventory. Skip-existing
and report comparison account for profile identity. No database migration.

For this laptop we provisioned .NET SDK 10.0.100 (macOS x64) and Microsoft's
Microsoft.NETFramework.ReferenceAssemblies.net48 1.0.3 package. There are 5,151 pinned
files including 237 reference DLLs. The profile is under work/slice46-dependencies;
the SDK and references are intentionally not committed. This SDK is platform-specific:
OpenShift requires a matching Linux image/toolchain, not copying macOS executables.

## Reproduce and use

Pre-provision approved SDK and references under a common directory, then pin them:

```sh
uv run python scripts/pin_csharp_dependencies.py DEPENDENCY_ROOT --sdk dotnet --references references/net48 --sdk-version 10.0.100 --codeql-version 2.27.0
veriflow scan-run RUN_ID CSHARP_QUERY_PATH --language csharp --allow-csharp-downloads --csharp-dependency-profile DEPENDENCY_ROOT/profile.json
uv run python scripts/validate_csharp_classic.py CSHARP_QUERY_PATH NEW_OUTPUT_DIRECTORY --csharp-dependency-profile DEPENDENCY_ROOT/profile.json
```

The pinning script creates profile.json once and performs no downloads. Profile
versions must match the supplied tools; do not blindly copy the example versions for
another platform. Keep the shared SDK/reference tree read-only during production scans.
The local implementation checks hashes before/after; it does not enforce a filesystem
mount policy. SDK hashing currently happens per verification and needs measured reuse
optimization before fleet deployment. Use separate writable scratch per scan.

queries/diagnostics/csharp/parameter-types.ql reproduces the unknown/resolved parameter
type check using codeql query run followed by codeql bqrs decode. It is a diagnostic,
not a vulnerability query. The query pack pins csharp-all 7.3.0 for the current toolchain.

## Offline and enterprise boundary

On 2026-09-10, after the session permissions changed, the classic vulnerable/fixed
fixtures passed under macOS sandbox-exec with `(deny network*)`: one candidate for
the vulnerable fixture and zero for its parameterized counterpart. A direct socket
probe and a spawned Python child both received PermissionError (Operation not
permitted) under the same policy. The earlier sandbox_apply failure is resolved.
The full validation used a fresh output/state directory, made no model calls and
retained incomplete report readiness. Results: work/slice46-offline/validation.json.

Reproduce on a macOS host that permits applying the sandbox (output must not exist):

```sh
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' .venv/bin/python scripts/validate_csharp_classic.py CSHARP_QUERY_PATH NEW_OUTPUT_DIRECTORY --csharp-dependency-profile work/slice46-dependencies/profile.json
```

This qualifies the pinned fixture pair under externally enforced local network denial.
It does not make ordinary CLI scans isolated: the application does not install or
attest this external sandbox. Consequently report network_denial_verified remains
false and --allow-csharp-downloads is still required by the current CLI. The external
sandbox denies attempted access despite that flag. Do not interpret the report field
as an attestation of this test harness, or the fixture result as broad project coverage.
Linux network-none container validation remains open. Private-feed support is not
implemented by this first local reference profile; pre-provisioned reference DLLs
are supported.

Production plan: pinned platform-specific SDK/CodeQL in an approved worker image;
read-only, versioned dependency sets on PVC or approved internal feed; per-scan scratch;
network-deny by default; explicit approved registry access only in preparation jobs.
Classic projects needing full Windows/MSBuild tooling require a separate constrained
Windows worker coordinated by the OpenShift control plane. That worker remains planned.

C# semantic indexing, LLM evidence policies, Razor/generated-code qualification and
broader classic/Core ASP.NET coverage remain open. Reports still say incomplete.
No live model calls or bank source were used.

## Sources

- [Microsoft reference assemblies](https://learn.microsoft.com/en-us/dotnet/framework/migration-guide/reference-assemblies)
- [CodeQL dependency manager source](https://github.com/github/codeql/blob/main/csharp/extractor/Semmle.Extraction.CSharp.DependencyFetching/DependencyManager.cs)
- [CodeQL C# environment settings](https://github.com/github/codeql/blob/main/csharp/extractor/Semmle.Extraction.CSharp.DependencyFetching/EnvironmentVariableNames.cs)

The upstream source informed the configuration; the installed CodeQL 2.27.0 fixture
runs provided the local behavior evidence.

Final validation: 413 regression tests passed; real profile-backed classic vulnerable/
fixed cases passed with 1/0 candidates. Lint, formatting and package builds passed.
