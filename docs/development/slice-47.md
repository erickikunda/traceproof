# Slice 47: fail-closed local C# offline extraction

Slice 46 committed as e48b19a. This slice adds `--csharp-offline` to codeql-extract,
scan-run and scan-import. It requires a pinned C# dependency profile and rejects
combining offline mode with --allow-csharp-downloads. Automatic single-language
selection can select C# before this validation. No database migration.

## Behavior and boundary

On macOS, a fixed sandbox-exec policy denies network operations. A Python gate checks
that a loopback connection fails with EPERM inside the sandbox, then execs the trusted
tool without leaving that sandbox. The same wrapper covers SDK version inspection,
CodeQL version inspection and database creation, including extractor child processes.
Unexpected probe results fail closed. An unavailable platform, sandbox or failed
preflight is retained as network_isolation_unavailable; no extraction is launched.
There is no automatic network-enabled fallback.

The extraction scope records network_isolation=macos-network-deny-v1 and
extractor_downloads_allowed=false. After successful isolated extraction, the pinned
profile scope records network_denial_verified=true. Failed attempts retain false.
Scan reuse includes isolation mode; comparison version 6 reports differing modes.
The flag does not sandbox the entire pipeline, query execution or model transport.
It provides network isolation for extraction only, not filesystem or hostile-build
containment. Source-only copying and existing process time/resource limits remain.

## Use

```sh
traceproof scan-run RUN_ID CSHARP_QUERY_PATH --language csharp --csharp-dependency-profile work/slice46-dependencies/profile.json --csharp-offline
.venv/bin/python scripts/validate_csharp_classic.py CSHARP_QUERY_PATH NEW_OUTPUT_DIRECTORY --csharp-dependency-profile work/slice46-dependencies/profile.json --csharp-offline
```

Do not add --allow-csharp-downloads to offline commands. The original opt-in download
path is unchanged. Linux currently fails closed for this flag: use an approved future
Linux worker implementation, not macOS executables copied into OpenShift.

## Validation and remaining scope

The real CodeQL 2.27.0 classic ASP.NET fixture pair is exercised using the pinned
.NET SDK 10.0.100/net48 profile, a fresh state directory and application-managed
network denial. Acceptance requires one vulnerable candidate, zero fixed candidates,
verified network denial in both reports and no model calls. Reports remain incomplete.
Both real cases passed with the expected 1/0 candidates and network denial verified.
Results are retained in work/slice47-offline/validation.json.

Tests cover incompatible configuration, unsupported hosts, durable preflight failure,
no network-enabled scan reuse, refusal to exec when a probe is unexpectedly allowed,
and actual macOS child-process network denial. The macOS integration test requires a
host that permits sandbox-exec; it deliberately fails if enforcement is unavailable.

Linux/OpenShift runner isolation, approved private feeds and Windows build workers
remain planned. Broader C#/ASP.NET Core/classic coverage and C# LLM evidence acceptance
remain open; offline fixture qualification does not imply those capabilities.
