# Local Linux container operator guide

This is the first OCP preparation image, qualified locally for synthetic Python, Java/Spring and C#/classic ASP.NET
source-only scan acceptance on Linux ARM64. It is not an OCP-certified deployment. No OpenShift
installation is needed on the laptop. Docker Desktop and uv are required for the
following commands; run from the TraceProof checkout.

## Build

```sh
uv run python scripts/build_container.py
```

Preparation downloads the checksum-pinned CodeQL 2.27.0 Linux ARM64 bundle into ignored
work/container-inputs, downloads/verifies the pinned Linux JDK, builds the application wheel and builds traceproof:linux-poc.
The UBI9 Python 3.12 image is pinned by manifest digest in containers/Containerfile.
Python runtime dependencies are installed from containers/requirements.lock with hash
verification and wheels only. Build needs registry/PyPI/GitHub access; runtime does not.
Downloaded CodeQL is verified against the committed hash, sourced from the release's
checksum file. Bank artifact approval, mirroring, signing and vulnerability scanning
are separate deployment prerequisites. No images are pushed by these scripts.

After changing uv.lock, refresh the exported dependency lock and review the diff:

```sh
uv export --frozen --no-dev --no-emit-project --format requirements-txt --output-file containers/requirements.lock
```

The current recipe is explicitly Linux ARM64, not a multi-architecture build. Confirm
bank worker architecture before preparing the matching AMD64 bundle/image. The UBI
base supports multiple architectures, but this CodeQL archive does not. No macOS SDK
or executable is copied into the image. The source-only Java lane uses a separately checksum-pinned full Temurin 21.0.12.1+1
Linux JDK, including jmods. Slice 49 identified missing inferred Spring artifacts. Slice 50 supplies a pinned
six-JAR local Maven repository alongside the full JDK; the JDK alone is insufficient.
Slice 51 adds Linux .NET SDK 10.0.100 and pinned net48 reference assemblies for
basic C# and classic ASP.NET fixtures. Slice 52 adds a separate ASP.NET Core MVC
fixture pair. Slice 53 adds a minimal API MapGet fixture pair. Broad classic MVC/Web API
coverage remains unqualified. No Maven/Gradle build execution is qualified.

## Run acceptance

```sh
uv run python scripts/validate_container.py work/container-acceptance-001
uv run python scripts/validate_container.py work/container-java-001 --suite java
uv run python scripts/validate_container.py work/container-csharp-001 --suite csharp
uv run python scripts/validate_container.py work/container-classic-001 --suite csharp-classic
uv run python scripts/validate_container.py work/container-core-001 --suite csharp-core
uv run python scripts/validate_container.py work/container-minimal-001 --suite csharp-minimal
uv run python scripts/validate_container.py work/container-webapi-001 --suite csharp-webapi
uv run python scripts/validate_container.py work/container-mvc-001 --suite csharp-mvc
# Spring suites automatically select the pinned fixture dependency profile.
uv run python scripts/validate_container.py work/container-spring-001 --suite spring
uv run python scripts/validate_container.py work/container-spring-maven-001 --suite spring --project-layout maven
uv run python scripts/validate_container.py work/container-spring-gradle-001 --suite spring --project-layout gradle
```

The output directory must be new. The test runs the inspected immutable image ID with:

- Arbitrary non-root UID 1000710000, group 0; all capabilities dropped.
- Read-only root filesystem, no-new-privileges, Docker default seccomp.
- No external network (`--network none`), no Docker socket or model credentials.
- Two CPUs, 4 GiB memory, 256 PIDs, bounded stage and overall timeouts.
- Separate tmpfs scratch for /work and /tmp; /reports binds only the new output directory.

Runtime probes check the applied process privileges, denied writes and external network
failure. Network-none retains loopback; it does not forbid communications within the
same container. The Python vulnerable/fixed/incomplete acceptance runs real CodeQL
extraction/querying and exact report retrieval. Java checks the vulnerable/fixed pair;
Spring attempts to check lookalike and incomplete cases, annotation observations, retained
source/sink flows and the narrow advisory evidence gate. The pinned profile restores the vulnerable candidate without enabling external network. Non-flat layouts select the
source-only Java profile and omit build configuration. These are synthetic annotation/
SQL fixtures, not deployed Spring applications or Maven/Gradle build qualification. SQLite state is temporary in /work;
this is deliberately not durable/shared-database qualification. Reports survive on the
host; state/databases disappear with the container. Execute permission on scratch is
needed for toolchain operation; no hostile source builds are enabled by this recipe.

The script removes only its own randomly named container. On failure it preserves CLI
output, container state and available extractor/query logs. A hard kill/OOM may prevent
log export from tmpfs; container-state.json records the runtime outcome. No background
services are started. A failed acceptance exits nonzero.

Outputs include validation.json, runtime.json, case-results.json, per-case JSON/HTML/
Markdown/CSV reports, image/runtime configuration, Python package inventory, observed Java version and RPM
package inventory. Inventories are not a formal SPDX/CycloneDX SBOM. Treat diagnostic
logs and reports as source-sensitive when adapting this workflow to real repositories.
The roughly 20-second synthetic first run is not a throughput benchmark.

## OCP preparation boundary

RHCOS is the node OS; dependencies belong in the image, approved volumes or service
endpoints. Do not mount host paths or Docker sockets into future worker pods. In OCP,
let the SCC assign the UID rather than copying this test UID into pod manifests.

Remaining work: broader Java/Spring dependency/version qualification;
broader C#/ASP.NET framework and evidence coverage; full Java build profiles; matching bank CPU
architecture; namespace Job/NetworkPolicy/PVC manifests; SELinux/SCC admission; corporate
CAs/mirrors; stage-separated egress and credentials; PostgreSQL durability; formal image
SBOM/signing/scanning; and finally the bank OCP smoke test. Actual cluster testing is
scheduled after functional POC completion. Local Docker success does not satisfy it.

The current --csharp-offline option uses macOS sandbox-exec and intentionally rejects
Linux. OCP/Docker isolation must be integrated as a distinct runner mode; do not pass
that flag inside this image or falsely report platform-enforced isolation as macOS
verification. LLM calls remain untested in this network-disabled acceptance run.

### Python interpreter selection

UBI's S2I shell startup normally prepends /opt/app-root/bin. The application image
sets BASH_ENV=/dev/null, and validation uses the absolute TraceProof virtual-environment
interpreter for fixture scripts and package inventory. This avoids silently selecting
a different Python environment when starting the container through bash.

### Java source-only does not mean dependency-download-free

CodeQL build-mode=none can infer missing dependency artifacts and fetch them from
Maven Central. Detailed javac-extractor logs from the historical macOS run show fetches;
the offline Linux run logs show failed Spring artifact downloads and unresolved
annotation symbols. The traceproof profile name dependency-free describes operator
inputs, not extractor network behavior. Keep external network denied when testing
untrusted/bank source and do not treat zero candidates as a clean verdict. Reports
remain incomplete. Slice 50 supports --java-dependency-profile for approved pre-provisioned JARs. The
container fixture profile supplies six Spring 6.0.10 JARs. This is a fixed historical
fixture toolchain, not a recommendation to deploy that framework version.

### Pinned Java dependencies (Slice 50)

The container build verifies six JAR hashes from containers/java-profile.json and
copies them into a read-only image directory. Only preparation downloads artifacts.
The Spring acceptance suites pass --java-dependency-profile automatically; other Java
scans must select their own approved matching profile.

```sh
traceproof scan-run RUN_ID JAVA_QUERY --language java --java-dependency-profile DEPENDENCY_ROOT/java-profile.json
uv run python scripts/pin_java_dependencies.py DEPENDENCY_ROOT --repository maven-repository --artifact org.example:library:jar:1.0
```

Pinning does not download files. The local repository must contain exactly the specified
Maven-layout JARs. The first schema supports unclassified JAR coordinates only and pins
CodeQL 2.27.0 because the standalone classpath CSV interface is version-specific.
Additional repositories, POM-driven transitive resolution and arbitrary classpath flags
are not accepted by this interface. Approved inputs are hashed before/after extraction;
changed profiles prevent scan reuse and mark report comparison gaps. No migration.

A profile is not a network sandbox or a complete dependency-resolution guarantee.
CodeQL can still attempt inferred downloads for other unresolved symbols; the container
blocks those attempts. Even the passing fixture logs contain blocked fetch attempts.
Keep Docker --network none or future OCP egress policy in place. Reports retain
network_denial_verified=false because TraceProof does not attest the external Docker
policy; runtime.json/container-config.json are the separate local enforcement evidence.
Reports remain incomplete; no general framework reachability or production readiness
is inferred from the fixture results.

### Linux C# and classic ASP.NET (Slice 51)

Preparation verifies Microsoft's published SHA-512 for the .NET 10.0.100 Linux ARM64
SDK and the pinned SHA-256 for Microsoft.NETFramework.ReferenceAssemblies.net48 1.0.3.
Only reference DLLs are extracted from that package. An additional committed DLL
inventory is checked at image build, before generating the SDK/reference profile.
The generated profile is /opt/traceproof/csharp-dependencies/profile.json. It is
separate from the laptop's macOS SDK profile. Runtime rechecks the complete inventory.

--suite csharp runs the raw socket/SQL fixture pair; --suite csharp-classic runs the
System.Web.HttpRequest/SqlClient pair. Both use the installed C# SqlInjection query.
The fixture scripts retain the existing allow-csharp-downloads consent needed by the
CLI, while Docker --network none enforces external network denial. Do not remove that
runner restriction. Do not use the macOS-only --csharp-offline flag in this Linux image.

The report's network_denial_verified remains false because the app does not attest
external Docker policy. runtime.json and container-config.json are the enforcement
evidence. No LLM calls or .NET application builds occur in these synthetic fixtures.
C# semantic indexing/evidence support and real framework/build qualification remain
open. Linux success with reference assemblies does not imply Windows-only builds
can run on OCP. No shared-PVC/SQLite durability or OCP SCC/SELinux testing is claimed.

### ASP.NET Core MVC (Slice 52)

`--suite csharp-core` selects `/opt/traceproof/csharp-dependencies/core-profile.json`.
The image creates this profile from the already checksum-pinned .NET SDK 10.0.100,
using its .NETCore.App.Ref and AspNetCore.App.Ref 10.0.0 reference packs. The SDK and
reference files are inventoried and verified by the existing profile loader; runtime
integrity checks and report profile identity apply. No additional download is needed.
The net48 profile remains separate and unchanged.

The synthetic controller uses ApiController, Route, HttpGet and FromQuery annotations
with DbCommand SQL execution. The vulnerable concatenation produces one candidate;
the parameterized counterpart produces zero. Both retain incomplete readiness and
unsupported C# LLM evidence. This fixture does not establish minimal API, Razor,
Entity Framework, full project build or broad ASP.NET coverage. Container restrictions
and the distinction between external network denial and app attestation remain the
same as the other C# suites.

### ASP.NET Core minimal APIs (Slice 53)

`--suite csharp-minimal` uses the same `core-profile.json` as the MVC suite. It
exercises a MapGet lambda with an explicit FromQuery string and a FromServices
DbConnection. The pair compares SQL concatenation with a bound parameter. These
fixtures are scanned as source only; the application is never started.

This is a separate fixture qualification, not coverage of every minimal API binding,
HTTP verb, route group, filter, authorization policy or asynchronous handler. C# LLM
evidence remains unsupported and report readiness remains incomplete. The runner's
network denial is external; the application does not claim to attest it.

### Classic ASP.NET Web API (Slice 54)

`--suite csharp-webapi` selects `/opt/traceproof/csharp-dependencies/webapi-profile.json`.
This separate profile combines net48 with selected DLLs from Web API Core 5.3.0,
Web API Client 6.0.0 and Json.NET 13.0.3. `containers/webapi-packages.json` records the
NuGet URLs, package SHA-256s and exact DLL SHA-256s. Build preparation fetches and
checks packages; image construction verifies the DLL inventory before generating the
profile. Existing runtime profile integrity checks apply. This fixture scan requires no network.

These are selected metadata dependencies for the fixture, not a full NuGet restore
or dependency closure. Additional client dependencies, hosts and proprietary project
requirements need their own qualification. The pinned versions are fixture inputs,
not a recommendation to update bank applications to these versions.

The controller derives from System.Web.Http.ApiController and uses RoutePrefix,
Route, HttpGet and FromUri. A DbCommand concatenation is paired with a parameterized
fix. This does not qualify System.Web.Mvc controllers, model binders, filters, IIS,
Windows builds or C# LLM evidence. Readiness remains incomplete. The fixture source
is not executed; bank OCP validation remains a later acceptance gate.

### Classic ASP.NET MVC (Slice 55)

`--suite csharp-mvc` selects `/opt/traceproof/csharp-dependencies/mvc-profile.json`.
It combines net48 with six selected DLLs from MVC 5.3.0, Web Pages 3.3.0 and Razor
3.3.0. `containers/mvc-packages.json` pins official NuGet package URLs, archive hashes
and individual assembly hashes. The shared classic profile builder verifies the exact
inventory before creating separate MVC and Web API profiles. Runtime integrity checks
continue to apply. These versions are synthetic fixture inputs, not bank upgrade advice.

The fixture derives from System.Web.Mvc.Controller, uses RoutePrefix/Route/HttpGet,
and accepts a string action parameter. Its SQL concatenation and parameterized fix
are scanned under the same network-denied restrictions as the other suites. The source
is never executed. A separate compile sanity check of the trusted fixtures does not
enable builds of submitted repositories.

Razor DLLs provide metadata only: .cshtml files remain omitted. Full dependency closure,
custom binders, filters, view rendering, IIS/Windows builds and broad MVC coverage are
unqualified. C# LLM evidence remains unsupported and report readiness stays incomplete.

### C# advisory gate acceptance (Slice 56)

The existing `csharp-core` and `csharp-minimal` suites now additionally build a bundle
from the vulnerable result and check synthetic source/sink/flow/unknown-guard claims.
The gate must pass for review, keep reachability_proven=false and reject a negative
verdict. The validator exports vulnerable-bundle.json and vulnerable-gate.json alongside
the normal reports. No LLM call is made, so this tests evidence validation without
provider credentials or spend. Plain scans still require explicit triage to get advice.

The image includes the locked tree-sitter-c-sharp 0.23.5 grammar. Parsing occurs in an
isolated Python subprocess with a 10-second wall timeout, 5-second CPU limit, 16 KiB
source bound, 50,000-node bound and 512 MiB Linux address-space limit. macOS lacks the
same reliable address-space limit. This is a syntax parser, not a semantic C# index.

This updates the earlier Core fixture notes: a narrow FromQuery/CommandText evidence
gate is now available. Classic MVC/Web API and other C# sources still lack qualified
source evidence. Razor views, runtime guards and full builds remain unqualified.

### Classic evidence acceptance (Slice 57)

The `csharp-mvc` and `csharp-webapi` suites now also export a vulnerable bundle and
synthetic advisory gate result. Both must pass source/sink/flow/unknown-guard checks,
keep reachability_proven=false and reject negative advice. No LLM credentials or
calls are required. Core evidence behavior remains regression coverage.

This supersedes the earlier blanket exclusion of classic source evidence: support
now includes the narrow public HttpGet string-action patterns described in the CLI
guide. Raw System.Web request access, arbitrary binders/filters, other sink APIs,
full builds and broad framework semantics remain unqualified.

### JavaScript/TypeScript acceptance (Slice 58)

```bash
uv run python scripts/validate_container.py work/container-js-001 --suite javascript
uv run python scripts/validate_container.py work/container-ts-001 --suite typescript
```

These suites use the pinned CodeQL bundle's JavaScript extractor and
javascript-queries 2.4.5 CodeInjection.ql. Each supplies a distinct Express/eval
vulnerable/fixed source pair. The same arbitrary-UID, read-only-root, network-none
and resource restrictions apply. No repository package installation or application
execution occurs. Fixtures require one vulnerable candidate and zero fixed candidates,
completed query execution, correct language scope, incomplete readiness and zero model
calls. No additional bank network access or provider credentials are needed.

This is narrow fixture coverage. Package/tsconfig/module resolution, mixed JS/TS imports,
async and browser-framework behavior, source maps and JS/TS evidence gates remain open.
The application CLI accepts explicit JS/TS selections; the synthetic acceptance scripts
are not general-purpose scan submission commands.

## Experimental Joern Linux image

Joern has a separate image recipe, `containers/Containerfile.joern`, using the pinned
UBI base, Python wheel/dependencies, Temurin JDK 21 and Joern 4.0.625 Linux ARM64.
It contains no CodeQL or .NET toolchain. Pins are recorded in
`containers/joern-toolchain.json`; the build checks the local archive digests.

Prepare the approved archives under `work/container-inputs` (Joern ZIP and existing
JDK TAR.GZ), then run:

```sh
uv build
docker build -f containers/Containerfile.joern -t traceproof:joern-linux-poc .
uv run python scripts/validate_container.py work/joern-linux-check \
  --suite joern --image traceproof:joern-linux-poc
```

The output directory must be new. The harness resolves the immutable image ID and runs
with UID 1000710000/GID 0, read-only root, network none, all capabilities dropped,
no-new-privileges, 2 CPUs, 4 GiB RAM and 256 PIDs. Writable work/tmp are bounded tmpfs;
only the report directory is bind-mounted. The runtime probe checks effective privileges,
root-write denial and external-network denial before scanning. Build-time network for
Python packages is separate from network-disabled scan execution.

Seven synthetic Spring/JDBC cases exercise intake, discovery, source-bound candidates,
published reports and Joern evidence-policy isolation. HTML/JSON reports, raw application
logs, runtime probe, package inventories, Docker configuration/state and validation summary
are exported. Temporary database/graphs disappear with the container. This validates
local restricted Linux execution, not durable shared storage or OCP deployment.

Application reports conservatively do not attest to externally imposed network isolation;
consult `runtime.json` and Docker configuration for the harness enforcement evidence.
Parser diagnostics and broader Java/framework coverage remain unqualified even when the
container suite passes. Bank OCP testing remains required and deferred as agreed.

Slice 68 expands the Joern suite to nine cases, adding wholly malformed Java and valid
cross-file code alongside a malformed file. Both must retain parser warnings and missing
graph-file coverage without claiming complete analysis; the mixed case retains its valid
candidate. The same `--suite joern` command runs the expanded suite.

### Experimental repaired Joern C# qualification

This local-only image layers the isolated C# frontend repair on the existing pinned
Joern Linux ARM64 image. It does not register a production C# backend. Prepare the
pinned AstCreator.scala identified in scripts/joern/csharp-repair/manifest.json at
work/container-inputs/AstCreator.scala; the build helper checks its SHA-256.

```sh
uv build
docker image inspect traceproof:joern-linux-poc --format '{{.Id}}'
docker build --network=none -f containers/Containerfile.joern-csharp \
  -t traceproof:joern-csharp-linux-poc .
uv run python scripts/validate_container.py work/joern-csharp-linux-new \
  --suite joern-csharp --image traceproof:joern-csharp-linux-poc
```

The recipe defaults to a local base tag; record/verify its immutable ID against the
qualified base and do not assume a reused tag identifies the same tools. Building a
production release from a registry digest and pinning the patch are separate work.
The acceptance runner resolves the final image ID before execution.

The suite tests ten original C# cases and ten adversarial binding cases, then replays
18 baseline path nodes through source mapping and checks seven source/five sink syntax
fact attachments (some source nodes refer to the same parameter). Runtime restrictions
are the same arbitrary UID, read-only root, network none, dropped capabilities, no-new-
privileges, 2 CPUs, 4 GiB memory, PID and tmpfs limits as the other local suites. Image
compilation happens at build time; scanned applications are not built or executed.

Results include runtime.json, baseline-results.json, binding-results.json, framework.json,
build-receipt.json, case-results.json, validation.json, native environment inventories and
stage logs. A failure exports available logs; success requires all cases and evidence
checks. No API keys or bank data are required. Actual bank OCP SCC/SELinux/PVC behavior,
upstream patch qualification and broader C# semantics remain separate acceptance gates.

The C# suite also runs two durable discovery cases (22 total): source-archive intake,
SQLite persistence, scan retrieval, HTML/JSON publication and evidence-bundle gating.
The vulnerable/fixed pair must yield 1/0 candidates, all published paths must validate,
and both reports must remain incomplete. Exported durable-vulnerable.html and
durable-fixed.html can be shared; durable-*.json contains scan reports and case results.
This acceptance run uses synthetic sources and no LLM. It does not measure production
throughput or validate PostgreSQL, cluster scheduling, or bank OCP deployment.

## Experimental Python Joern integration

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-python \
  -t traceproof:joern-python-linux-poc .
uv run python scripts/validate_container.py work/joern-python-linux-new \
  --suite joern-python --image traceproof:joern-python-linux-poc
```

Uses the same trusted local Joern base and records the final immutable image ID.
Five existing synthetic cases exercise durable intake/discovery/report retrieval,
single-file and cross-file vulnerable/fixed pairs, and disconnected input. Recorded
source snippets must match their reported lines. All cases retain incomplete coverage
and unsupported qualified triage. HTML/JSON reports and environment evidence are exported
under the supplied new output directory. No LLM calls or application builds are needed.
The standard restricted runtime applies; this is local Linux acceptance, not bank OCP
or throughput qualification.

## Experimental JavaScript/TypeScript Joern integration

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-javascript \
  -t traceproof:joern-javascript-linux-poc .
uv run python scripts/validate_container.py work/joern-js-linux-new \
  --suite joern-javascript --image traceproof:joern-javascript-linux-poc
uv run python scripts/validate_container.py work/joern-ts-linux-new \
  --suite joern-typescript --image traceproof:joern-javascript-linux-poc
```

The shared image uses the trusted local Joern base; each run records its immutable ID.
Run suites sequentially on the laptop to stay within its memory budget. Each uses five
existing fixtures, including ES-module cross-file and disconnected-flow cases, through
archive intake, persistence and report retrieval. Source snippets must match reported
lines; coverage remains incomplete. Output includes HTML/JSON reports and runtime
evidence. Standard restricted Linux limits apply. These are bounded local integration
checks, not full framework, mixed-language, production capacity or OCP qualification.

## Experimental Go Joern integration

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-go \
  -t traceproof:joern-go-linux-poc .
uv run python scripts/validate_container.py work/joern-go-linux-new \
  --suite joern-go --image traceproof:joern-go-linux-poc
```

This local image layer uses the trusted Joern base; the runner records its immutable ID.
Five existing dependency-free module fixtures cover single-file and three-package
vulnerable/fixed pairs plus disconnected input. The normal restricted runtime applies.
Acceptance checks persistent report retrieval, source coordinates, graph inventory and
incomplete coverage. HTML/JSON reports and runtime evidence are exported to the new
output directory. No application build or LLM call is requested. This is not a capacity
benchmark or actual bank OCP qualification.

## Experimental Rust Joern integration

Prepare the official Linux ARM64 Rust and rust-src archives identified in
`scripts/joern/rust-linux-toolchain.json` at `work/container-inputs/rust-linux-arm64.tar.xz`
and `work/container-inputs/rust-src.tar.xz`. The image build checks both digests.

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-rust \
  -t traceproof:joern-rust-linux-poc .
uv run python scripts/validate_container.py work/joern-rust-linux-new \
  --suite joern-rust --image traceproof:joern-rust-linux-poc
```

The Rust runtime uses digest-pinned UBI 10 Python 3.12 Minimal because the bundled
Rust AST generator requires GLIBC 2.39; the other language images stay on UBI 9.
The image installs the pinned rustc, cargo, target standard library and rust-src from
local archives. Five dependency-free Cargo fixtures exercise durable reports and
single-file/cross-file vulnerable/fixed plus disconnected flows. The normal restricted
Linux runtime applies; no application execution or LLM calls are requested. This does
not qualify arbitrary Cargo dependencies, procedural macros, cfg/build semantics, bank
OCP deployment or production capacity. HTML/JSON and runtime evidence are exported.

## Experimental C/C++ Joern integration

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-c-family \
  -t traceproof:joern-c-family-linux-poc .
uv run python scripts/validate_container.py work/joern-c-linux-new \
  --suite joern-c --image traceproof:joern-c-family-linux-poc
uv run python scripts/validate_container.py work/joern-cpp-linux-new \
  --suite joern-cpp --image traceproof:joern-c-family-linux-poc
```

Run sequentially on the laptop. Each suite reuses five existing fixtures: single-file
and three-translation-unit vulnerable/fixed pairs with shared declarations, and a
disconnected-input negative. Checks include persistent report retrieval, source-line
agreement, graph inventory and incomplete coverage. The shared image uses the trusted
UBI 9 Joern base; standard restricted Linux limits apply. HTML/JSON and runtime evidence
are exported. No LLM calls, application build or production capacity/OCP qualification.

## Main Joern workflow acceptance

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-pipeline \
  -t traceproof:joern-pipeline-linux-poc .
uv run python scripts/validate_container.py work/joern-pipeline-linux-new \
  --suite joern-pipeline --image traceproof:joern-pipeline-linux-poc
```

The existing Python fixtures exercise scan-import, auto language selection, exact-attempt
publication, batch retry suppression and a fresh direct scan-run. The suite makes six
actual scans across five cases. Standard restricted Linux limits and incomplete coverage
gates apply. This is shared orchestration acceptance, not a repeat qualification of every
language frontend. Per-language tool requirements and image acceptance remain documented
in their own sections. No LLM calls, distributed scheduling or OCP qualification.

## Flask profile acceptance

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-flask \
  -t traceproof:joern-flask-linux-poc .
uv run python scripts/validate_container.py work/joern-flask-linux-new \
  --suite joern-flask --image traceproof:joern-flask-linux-poc
```

Eight cases cover direct and cross-file vulnerable/fixed pairs, renamed/aliased input,
shadowed request/os bindings and disconnected flow. Main scan-import/report publication
and retry skipping are exercised, plus one direct rescan. Source-line assertions apply
to the path endpoints; synthetic intermediate nodes are retained without such a claim.
Standard restricted Linux conditions apply; no model calls or application execution.

## Express profile acceptance on the laptop

Build the shared JavaScript/TypeScript profile layer after building the pinned Joern
base described above, then run the suites sequentially within Docker Desktop's memory:

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-express \
  -t traceproof:joern-express-poc .
uv run python scripts/validate_container.py work/express-js-acceptance \
  --suite joern-express-javascript --image traceproof:joern-express-poc
uv run python scripts/validate_container.py work/express-ts-acceptance \
  --suite joern-express-typescript --image traceproof:joern-express-poc
```

Each suite exercises eight synthetic cases through CSV intake, automatic language
selection, main pipeline scanning, publication/retrieval, profile-aware retry skipping
and evidence gates; the fixed case also receives a fresh explicit scan. The runner uses
an arbitrary UID, read-only root, dropped capabilities, no network, and bounded resources.
No LLM calls are made. Laptop Linux acceptance does not qualify deployment to bank OCP.

## Go HTTP profile acceptance on the laptop

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-go-http \
  -t traceproof:joern-go-http-poc .
uv run python scripts/validate_container.py work/go-http-acceptance \
  --suite joern-go-http --image traceproof:joern-go-http-poc
```

Use the pinned Joern base prepared above. Nine synthetic cases cover direct/cross-package
pairs, disconnected data, aliases/PostFormValue, lookalike imports and a non-shell
command. Main intake/scanning, publication/retrieval, retry suppression and evidence
gates are exercised with no LLM calls; the fixed case is also explicitly rescanned.
The runner enforces arbitrary UID, read-only root, disabled network and resource limits.
Reports and immutable image identity are exported to the output directory. This is local
Linux acceptance; bank OCP deployment testing remains a separate deferred gate.

## C/C++ argv profile acceptance on the laptop

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-argv \
  -t traceproof:joern-argv-poc .
uv run python scripts/validate_container.py work/argv-c-acceptance \
  --suite joern-argv-c --image traceproof:joern-argv-poc
uv run python scripts/validate_container.py work/argv-cpp-acceptance \
  --suite joern-argv-cpp --image traceproof:joern-argv-poc
```

Use the pinned Joern base prepared above and run the suites sequentially. Each suite has
eight cases: direct and cross-file pairs, renamed array syntax, disconnected flow,
non-main source and local system definition. Main intake/scanning, report publication
and retrieval, endpoint coordinates, graph inventory and retry/evidence gates are checked.
The fixed case also receives a fresh explicit scan. There are no LLM calls.
The runner uses arbitrary UID, read-only root, no network and bounded resources, exporting
reports and immutable image identity. Actual bank OCP testing remains a deferred gate.

## Rust environment profile acceptance on the laptop

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-rust-env \
  -t traceproof:joern-rust-env-poc .
uv run python scripts/validate_container.py work/rust-env-acceptance \
  --suite joern-rust-env --image traceproof:joern-rust-env-poc
```

This layer uses the previously prepared pinned Rust UBI 10 image and its /opt/rust
toolchain. The UBI 9 Joern base is insufficient for the pinned Rust AST generator.
Nine synthetic cases exercise direct/cross-module pairs, aliases, disconnected flow,
lookalike source/sink APIs and a non-shell command. The main intake/scan/report workflow,
retry suppression, graph inventory, endpoint coordinates and incomplete evidence gates
are checked. Fixed input is also explicitly rescanned. No LLM calls occur.

The runner uses arbitrary UID, read-only root, no network and bounded resources and
exports image identity, diagnostics and shareable reports. This remains laptop Linux
acceptance; bank OCP execution and base-image approval are deferred gates.

## Joern Spring evidence-gate acceptance

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-spring-evidence \
  -t traceproof:joern-spring-evidence-poc .
uv run python scripts/validate_container.py work/spring-evidence-acceptance \
  --suite joern-spring-evidence --image traceproof:joern-spring-evidence-poc
```

Seven existing Java fixtures exercise native discovery and report publication. Vulnerable
and renamed cross-file candidates additionally pass the explicit evidence gate using
synthetic deterministic claims, not LLM-generated judgments. Fixed/disconnected and
annotation/sink/route lookalikes remain zero-candidate controls. Exported *-gate.json files
retain the policy, engine and unknowns. No model calls occur. The same restricted Linux
runner and deferred bank OCP gate apply.

## Joern Spring replay advisory acceptance

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-spring-advisory \
  -t traceproof:joern-spring-advisory-poc .
uv run python scripts/validate_container.py work/spring-advisory-acceptance \
  --suite joern-spring-advisory --image traceproof:joern-spring-advisory-poc
```

Seven fresh Java scan cases are reused. The two positive cross-file candidates each receive
one explicit replay advisory, with native preflight, durable cost accounting, idempotent
retry and updated report publication. Zero live calls occur. The standard arbitrary-UID,
read-only-root, no-network and resource constraints apply. Exported *-advisory.json files
contain the ledger and the HTML reports include simulated advisory history. Target-bank
OCP acceptance remains deferred.

## Main Joern workflow with replay advisory

```sh
uv build
docker build --network=none -f containers/Containerfile.joern-workflow-advisory \
  -t traceproof:joern-workflow-advisory-poc .
uv run python scripts/validate_container.py work/workflow-advisory-acceptance \
  --suite joern-workflow-advisory --image traceproof:joern-workflow-advisory-poc
```

Seven native Java cases use the main scan-import path with preconfigured budgets and an
explicit replay advisory page. Acceptance checks per-run and aggregate invocation counts,
retry skips, immutable returned report IDs, simulated advice, and ledger charges. Five
negative cases make no provider calls. The usual restricted Linux controls apply; bank
OCP qualification remains deferred.

### Flask advisory workflow acceptance (Slice 99)

Using the locally prepared Joern base image:

```sh
uv build
docker build -f containers/Containerfile.joern-flask-advisory \
  -t traceproof:joern-flask-advisory-linux-poc .
uv run python scripts/validate_container.py --suite joern-flask-advisory \
  --image traceproof:joern-flask-advisory-linux-poc work/flask-advisory-acceptance
```

Choose a new output directory. Eight native fixture cases exercise discovery and three
positive advisory rescans, using synthetic replies derived from the initial fixture
bundles. No live provider runs. The harness checks budget accounting, duplicate suppression,
exact report retrieval and incomplete/unverified outcomes, exporting gates, bundles,
ledgers and HTML reports. The restricted local Linux run does not replace bank OCP testing.

### Express advisory acceptance (Slice 100)

Build the Joern acceptance layer with the updated hash-pinned Python requirements:

```sh
uv build
docker build -f containers/Containerfile.joern-express-advisory \
  -t traceproof:joern-express-advisory-linux-poc .
uv run python scripts/validate_container.py --suite joern-express-advisory-javascript \
  --image traceproof:joern-express-advisory-linux-poc work/express-advisory-js
uv run python scripts/validate_container.py --suite joern-express-advisory-typescript \
  --image traceproof:joern-express-advisory-linux-poc work/express-advisory-ts
```

Choose new output directories and run the two suites sequentially on the laptop. The
image build adds locked JS/TS parser binaries; runtime remains offline and executes no
repository packages. Each suite checks eight native cases and three replay advisory
rescans, exporting source/native evidence, gates, ledgers and shareable reports. The bank
must mirror the new dependencies as part of its normal image build process; local Linux
acceptance does not replace target OCP testing.

### Repaired C# advisory acceptance (Slice 101)

Using the previously prepared traceproof:joern-csharp-linux-poc image:

```sh
uv build
docker build -f containers/Containerfile.joern-csharp-advisory \
  -t traceproof:joern-csharp-advisory-linux-poc .
uv run python scripts/validate_container.py --suite joern-csharp-advisory \
  --image traceproof:joern-csharp-advisory-linux-poc work/csharp-advisory-acceptance
```

Choose a new output directory. The layer reuses the existing repair, installs the current
locked requirements and wheel, and adds the acceptance runner. Runtime remains offline
under the existing arbitrary-UID/read-only-root restrictions. Ten cases exercise Core,
MVC, Web API, cross-file flow, fixed input and misleading request sources. Four replay
advisories qualify; two candidate-bearing cases abstain without provider calls. Gates,
ledgers, native bundles and shareable HTML reports are exported. This is local Linux
acceptance and does not qualify the image for the bank's OCP environment.

### Go HTTP advisory acceptance (Slice 102)

```sh
uv build
docker build -f containers/Containerfile.joern-go-advisory \
  -t traceproof:joern-go-advisory-linux-poc .
uv run python scripts/validate_container.py --suite joern-go-advisory \
  --image traceproof:joern-go-advisory-linux-poc work/go-advisory-acceptance
```

Choose a new output directory. The layer uses the existing Joern base and the updated
hash-pinned Python requirements, including the Go grammar binary. Runtime remains offline,
with arbitrary UID, read-only root, dropped capabilities and bounded resources. Nine cases
exercise native discovery and three positive replay advisory rescans. The runner exports
gates, bundles, native output, ledgers and HTML reports; it makes no live model calls.
Bank package-mirror and actual OCP acceptance remain separate work.

### Rust environment advisory acceptance (Slice 103)

Use the existing traceproof:joern-rust-linux-poc base (UBI 10 and the trusted Rust toolchain):

```sh
uv build
docker build -f containers/Containerfile.joern-rust-advisory \
  -t traceproof:joern-rust-advisory-linux-poc .
uv run python scripts/validate_container.py --suite joern-rust-advisory \
  --image traceproof:joern-rust-advisory-linux-poc work/rust-advisory-acceptance
```

Choose a new output directory. Locked parser binaries are installed at image build time;
runtime remains offline under arbitrary UID, read-only root and bounded resources. Nine
cases exercise native discovery, including an eight-node cross-file path, with three
positive replay advisory rescans. The runner exports gates, bundles, native output,
ledgers and shareable HTML, without live model calls. Local acceptance does not replace
bank package approval or actual OCP execution.


## C/C++ advisory replay acceptance (Slice 104)

Build on the existing pinned Joern Linux base, then run the suites sequentially:

```sh
uv build
docker build -f containers/Containerfile.joern-argv-advisory -t traceproof:joern-argv-advisory-linux-poc .
uv run python scripts/validate_container.py --suite joern-argv-advisory-c --image traceproof:joern-argv-advisory-linux-poc work/argv-c-advisory
uv run python scripts/validate_container.py --suite joern-argv-advisory-cpp --image traceproof:joern-argv-advisory-linux-poc work/argv-cpp-advisory
```

Each suite expects eight cases and three replay advisories, zero live calls. Use a fresh
output directory. Dependency installation occurs at image build; runtime network is disabled.
The harness enforces the shared restricted runtime settings. This is laptop Linux fixture
acceptance, not bank OCP qualification or a throughput measurement.

## Offline OpenShift smoke bundle (Slice 106)

The [deployment guide](../../deploy/openshift/README.md) covers the pinned ARM64 image,
manifest rendering, one-row CSV/archive input, local Docker rehearsal and deferred cluster
steps. This is C argv-to-system discovery only, with ephemeral SQLite and exact JSON/HTML
exports. No Redis, LLM key or hosted API is required. Actual OCP admission/storage/network
acceptance has not been performed. The smoke image retains its pinned base application
version; rebuild that base explicitly when upgrading TraceProof.


Slice 107 supersedes the C-only smoke selection above: the entrypoint, renderer and rehearsal
runner accept `--language java|python|javascript|typescript|go|c|cpp`, selecting the existing
packaged discovery profile. See the deployment guide for the matrix. C#/Rust require separate
toolchain images; this smoke image rejects them. No advisory or language-coverage promotion.


Slice 108 adds separate `Containerfile.ocp-smoke-csharp` and `Containerfile.ocp-smoke-rust`
layers. Use the matching language and image in the renderer/rehearsal. The general smoke
image continues rejecting these languages. Each specialized layer retains its qualified
base wheel/toolchain snapshot; see the deployment guide for builds, fixed tool paths,
limitations and image-upgrade requirements. Zero model calls; OCP acceptance remains deferred.


Slice 113 supersedes the pinned-application limitations above. All three smoke recipes now
install the same freshly built application wheel and current hash-locked Python dependencies
over their existing toolchain bases. Run uv build before rebuilding, and use the exact
qualified digests in containers/ocp-smoke-images.json. Receipt-enabled intake and projection
13 are qualified locally in these refreshed images; older digests remain unchanged. The
build-input hash record is not a full SBOM or signature. Actual OCP remains deferred.


## Separate Git acquisition container (Slice 115)

Use Containerfile.git-acquisition for networked repositories.csv acquisition, then mount its
handoff output read-only in the offline scanner. See the
[acquisition container guide](acquisition-container-guide.md) for build/run commands, exact
path preservation, partial-batch handling and security/enterprise limitations. Public HTTPS
only; no private credentials or actual OCP qualification. No automatic scan dispatch.
