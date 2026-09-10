# Slice 54: Classic ASP.NET Web API offline qualification

Slice 53 committed as `af16fd7`. This slice adds a distinct classic Web API fixture
suite and pinned dependency profile. No schema migration or application scan-policy
change is required.

## Implementation

The synthetic System.Web.Http.ApiController binds a FromUri string and constructs a
DbCommand. RoutePrefix belongs to the controller; Route and HttpGet belong to the
action. The fixed counterpart binds a SQL parameter. Acceptance requires 1/0 SQL
candidates, completed analysis, incomplete readiness and zero model calls.

The Web API profile combines net48 references with System.Web.Http,
System.Net.Http.Formatting and Newtonsoft.Json DLLs. Package and assembly SHA-256
pins are committed in containers/webapi-packages.json. Cached/downloaded packages
are verified before extraction, and image build checks the exact assembly inventory.
The existing profile loader and runtime integrity checks validate the resulting
webapi-profile.json. Core and basic net48 profiles remain separate.

Web API Core 5.3.0 metadata declares Client 6.0.0; the selected Json.NET version is
13.0.3. These selected assemblies support the fixture, not complete dependency closure.
The package also declares other transitive dependencies that this fixture does not
exercise. Package provenance: [Microsoft's NuGet listing](https://www.nuget.org/packages/Microsoft.AspNet.WebApi.Core/5.3.0).
Downloads used official NuGet HTTPS endpoints; available publisher SHA-512 response
metadata was checked during initial pinning. The build uses committed SHA-256 pins.
No cryptographic publisher-signature verification is claimed.

## Validation

All 433 automated tests, Ruff lint/format and package/image builds passed. Both trusted
fixture sources also compile as libraries with the pinned SDK and required local
references under network denial; compiled code was not executed. This fixture sanity
check does not enable builds of submitted repositories.

Final Web API and classic regression suites passed: 1/0 candidates each, in
50.935 and 49.769 seconds respectively. These are synthetic
fixture timings, not throughput qualification. Image: `sha256:f1fe213319e340fd9bf7aee3dbfa00a216089d43ebfe1a8670966e3a8a61ab04`.
Artifacts: work/slice54-webapi-final, work/slice54-classic and
work/slice54-fixture-compile.log. Runtime uses arbitrary
non-root UID, read-only root filesystem, network-none and bounded resources. The
application continues to report external network denial as unattested.

## Boundaries and next work

This establishes only the described classic Web API SQL path. Classic MVC, additional
binding patterns, authorization filters, IIS/Windows hosting and full project builds
remain unqualified. C# LLM evidence remains open. Next: classic MVC qualification and
C# evidence, then JavaScript/TypeScript. OCP testing stays deferred until functional
POC completion. No bank source or live model was used; no image was pushed.
