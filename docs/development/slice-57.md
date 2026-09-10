# Slice 57: Classic MVC/Web API SQL advisory evidence

Slice 56 committed as `a78e02e`. Gate 7 adds narrow classic action-parameter source
checks to the existing C# SQL advisory pipeline. No new dependencies or migration.

## Supported shape

A direct public System.Web.Mvc.Controller or System.Web.Http.ApiController class
contains a public instance HttpGet action accepting a string. MVC parameters have no
binding attributes; Web API parameters have exactly FromUri. Matching namespace imports
or qualified names provide syntax hints. The sink remains a CommandText assignment.
Claims must match complete bounded source context and the endpoints of a complete
retained CodeQL path. Parser resource limits and immutable bundle behavior are unchanged.

Private/static/abstract/override or generic action shapes, NonAction or other method
attributes, parameter-binding variations, unrelated bases, mixed framework imports and
local framework-name lookalikes fail closed. These restrictions are deliberately narrow:
no runtime routing, foreign-file binding, authorization or exploitability proof is made.
A passing result remains supported_for_review, with unknown guard effectiveness and
reachability_proven=false. Negative advice still cannot pass or suppress a finding.

The adapter capability is aspnet_sql_review_v2. Existing comparison logic flags changes
from the Core-only policy. Existing persisted reports remain unchanged. Gate-version
identity prevents silently reusing older triage requests under the new policy.

## Validation

Unit coverage includes both positive classic gate cases and rejection of action/base,
namespace, shadowing, attribute and generic/abstract variants. The real classic MVC and
Web API container suites now build retained-path bundles and assess synthetic decisions;
no model call is involved. A Core regression checks the shared parser/gate.

476 automated tests, Ruff lint/format and package/image builds passed. MVC, Web API
and Core container pairs passed with 1/0 candidates each and supported_for_review
gates that reject negative advice. Timings were 65.445, 61.636, 48.455 seconds
respectively; these are synthetic fixture timings, not a capacity measurement.
Image: `sha256:5eb99521990907fe4b78500230e5c74131469c40d0457b1f0354312acd441183`.
Evidence: work/slice57-csharp-mvc, work/slice57-csharp-webapi and work/slice57-csharp-core. The scope is local Linux ARM64 qualification, not
bank OCP or fleet-throughput acceptance. No live model, bank source or image push.

## Next priority

Proceed to L3 JavaScript/TypeScript. L2 remains partial: broader C# bindings and sinks,
guard evidence, semantic resolution, Razor and full/Windows builds stay tracked as
explicit qualification obligations rather than implied coverage.
