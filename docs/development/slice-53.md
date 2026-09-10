# Slice 53: ASP.NET Core minimal API offline qualification

Slice 52 committed as `2dedcfa`. This slice adds the csharp-minimal container suite,
a dedicated fixture wrapper and a vulnerable/fixed MapGet pair. No schema migration
or new runtime dependencies are needed.

## Behavior

A WebApplication registers a MapGet lambda with a FromQuery string and a FromServices
DbConnection. Concatenating that string into a DbCommand produces one cs/sql-injection
candidate. Replacing concatenation with a bound parameter produces zero candidates.
The existing validator also requires completed analysis, correct language and rule,
incomplete readiness and no model calls. It never executes the fixture application.

Both cases use the Core profile created from the pinned .NET SDK and reference packs.
The net48 profile remains separate. The container runs with networking disabled,
arbitrary non-root UID, read-only root filesystem, dropped capabilities, no privilege
escalation and CPU/memory/PID limits. Report network_denial_verified remains false
because enforcement belongs to the Docker runner rather than the application.

## Validation

The minimal API pair passed in 50.094 seconds. All 433 automated tests and Ruff checks
passed; package/image builds and git diff whitespace validation passed. The Core MVC
pair also passed on the same image in 50.51 seconds (1/0 candidates).

Image: `sha256:ad425cc2104ea696ee3847a01f410cde32f1722d8539d6464c0601ab426ba1f4`.
Evidence: work/slice53-minimal and work/slice53-core. Run the container operator guide's
csharp-minimal and csharp-core commands with new output directories to reproduce.

## Remaining scope

This is a narrow synthetic MapGet/SQL qualification, not a broad minimal API claim.
Other bindings, verbs, filters, route groups, authorization and async handlers remain
unqualified. C# LLM evidence, broad classic MVC/Web API and full builds remain open.
Next: classic framework qualification and C# evidence, followed by JavaScript/TypeScript
as the implementation plan specifies. Bank OCP validation remains deferred until the
functional POC is complete. No bank source, model calls or image push were involved.
