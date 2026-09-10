# Slice 52: ASP.NET Core MVC offline fixture qualification

Slice 51 committed as `162f13f`. This slice adds a separate Core MVC fixture suite
and dependency profile to the existing Linux ARM64 image. No schema migration.

## Implementation

The build derives core-profile.json from the pinned Linux SDK 10.0.100 and its
matching .NETCore.App.Ref/AspNetCore.App.Ref 10.0.0 reference packs. Each pack stays
in a separate directory; the manifest inventories all reference files and reuses the
SDK inventory. The existing profile loader validates the generated manifest. Missing
packs fail the build. Classic ASP.NET continues to use the independent net48 profile.

The new csharp-core suite exercises an ApiController with HttpGet and FromQuery,
followed by DbCommand SQL execution. Its paired fix uses a bound SQL parameter.
The shared validator requires one vulnerable candidate and zero fixed candidates,
completed analysis, the C# SQL rule, incomplete readiness and zero model calls.

## Validation and limits

The Core pair passed in 48.113 seconds under arbitrary UID, read-only root filesystem,
network-none, dropped capabilities and resource limits. This is a synthetic fixture
timing, not a fleet throughput measurement. All 433 automated tests, Ruff lint/format,
package and image builds passed. The classic ASP.NET regression pair also passed on the same image in
50.455 seconds, with one vulnerable candidate and zero fixed candidates.

Image: `sha256:9940f8528c5ab30fc69adf5bd6a0306c59f03a36454c50939f00311ca3f4dcda`.
Evidence: work/slice52-core and work/slice52-classic. Reproduce with the container
operator guide's csharp-core and csharp-classic commands.

This qualifies only the described Core MVC SQL fixture. Minimal APIs, Razor, Entity
Framework, broad classic MVC/Web API, C# semantic/LLM evidence and full builds remain
open. Actual bank OCP testing stays deferred to functional POC completion. No live
model or bank source was used, and no image was pushed. No user action is needed.
