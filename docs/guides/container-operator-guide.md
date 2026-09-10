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
