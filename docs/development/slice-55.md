# Slice 55: Classic ASP.NET MVC offline qualification

Slice 54 committed as `0e1c5c1`. This slice adds classic MVC Controller/action-parameter
SQL fixtures and a separate dependency profile. No database migration.

## Implementation

The MVC fixture uses System.Web.Mvc.Controller with RoutePrefix, Route and HttpGet.
A string action parameter flows into DbCommand SQL concatenation. The paired fix uses
a bound parameter. The shared acceptance validator requires one vulnerable candidate,
zero fixed candidates, completed analysis, correct rule/language, incomplete readiness
and zero model calls.

The MVC profile adds six DLLs from MVC 5.3.0, Web Pages 3.3.0 and Razor 3.3.0 to net48.
Package URLs and SHA-256 pins are recorded in containers/mvc-packages.json, including
individual DLL hashes. Initial downloads used official NuGet HTTPS endpoints and
checked available publisher SHA-512 response metadata. No publisher-signature claim.
The package's nuspec declares the Web Pages and Razor versions; these are selected
fixture metadata dependencies, not a complete application restore.

The build now shares archive preparation across Web API and MVC. The renamed
prepare_classic_profile.py accepts only those two families, checks exact inventories
and creates independent profiles. Existing profile loading and runtime integrity checks
are unchanged. The Web API regression suite checks this refactor on the same image.

## Validation

All 433 automated tests, Ruff checks and package/image builds passed. Both trusted MVC
fixture sources compile as libraries with the pinned SDK/local references under network
denial; compiled code was not executed. CodeQL scans remain source-only.

MVC and Web API regression pairs passed with 1/0 candidates each in
57.011 and 54.889 seconds respectively.
Image: `sha256:a05bdb0d99259bebd1c9822b7c08ba9be4c720a34fd280d10814528144f32d7f`.
Artifacts: work/slice55-mvc, work/slice55-webapi and work/slice55-fixture-compile.log. This is local ARM64 evidence,
not bank OCP or fleet throughput qualification.

## Remaining scope

This qualifies only the described MVC SQL fixture. Additional binders, async actions,
filters, views, IIS/Windows builds and full dependency closure remain open. Razor
reference DLLs do not enable scanning Razor views. C# evidence support is next, followed
by JavaScript/TypeScript. Bank OCP testing remains deferred until functional POC
completion. No bank source, live model calls or image push was involved.
