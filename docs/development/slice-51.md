# Slice 51: Linux C# and classic ASP.NET container qualification

Slice 50 committed as 0e24f72. This slice extends the Linux ARM64 image with a
separate pinned .NET SDK/reference profile and adds two C# container fixture suites.
It does not modify application scanning semantics or require a database migration.

## Supplied toolchain

The .NET SDK 10.0.100 Linux ARM64 archive is verified against the SHA-512 from
Microsoft's .NET 10 release metadata, recorded in containers/toolchain.json. The
net48 1.0.3 reference package is SHA-256 pinned. Preparation extracts only its DLLs,
and image build verifies them against containers/net48-inventory.json before pinning
the combined profile. The image includes 5,152 pinned SDK/reference files, including
237 reference DLLs. Existing runtime pre/post hash checks apply to this profile.

The generated profile is /opt/veriflow/csharp-dependencies/profile.json; the macOS
profile under work/slice46-dependencies is unchanged. UBI supplies ICU/OpenSSL native
libraries through the pinned base image. No runtime package installation is needed.
Build preparation uses network access; fixture execution denies external networking.

## Acceptance and boundary

--suite csharp exercises the existing socket-input/SQL pair. --suite csharp-classic
exercises System.Web.HttpRequest.QueryString/SqlClient. These are distinct fixture
suites; neither qualifies ASP.NET Core MVC/minimal APIs or broad classic MVC/Web API.
They run as UID 1000710000 with no capabilities, no privilege escalation, a read-only
root filesystem and bounded CPU/memory/PIDs. Only scratch/report mounts are writable.

The existing fixture scripts pass explicit C# download consent required by the CLI;
Docker network-none prevents external connections. The macOS --csharp-offline flag is
not used. Report network_denial_verified=false remains correct because the application
does not attest the external Docker runner. Runtime/config artifacts establish local
network-denial evidence separately. Reports remain incomplete and C# LLM evidence is
unsupported. No live model calls, analyzed application builds or bank source were used.

The initial Linux classic pair passed with one vulnerable candidate and zero fixed
candidates. The finalized image is also tested against basic C#, Python, Java and
Spring to detect packaging regressions. Final results: all five suites passed (13 synthetic cases total). C# and classic
ASP.NET each produced 1/0 candidates. Python/Java/Spring regression fixtures passed.
433 automated tests, lint/format checks and package/image builds passed.

Final image: `sha256:b3c0e4020906522993b1a30d7236937d83739f047f682cd427db94c3e1ba06b7`.
Linux profile: `883e0372b3f69c42e557c463e4f93552faeea2a1063507d7f0040e07492a7c5f`.
Artifacts are under work/slice51-final-SUITE, including runtime/configuration evidence
and per-case reports. These synthetic timings are not throughput qualification.

OCP dev testing remains deferred until functional POC completion, as requested. SCC,
SELinux, PVC/PostgreSQL durability, AMD64 and Windows-only build workflows remain open.
No image was pushed; no user action is needed for the next local implementation slice.

Reproduce using the [container operator guide](../guides/container-operator-guide.md).
