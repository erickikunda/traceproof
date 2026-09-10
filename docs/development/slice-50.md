# Slice 50: pinned Java dependencies and offline Spring acceptance

Slice 49 committed as 44cefbc. This slice addresses the diagnosed offline Spring miss
by supplying approved JAR dependencies, keeping the network-deny container unchanged.

## Implementation

--java-dependency-profile is available on extraction, scan-run and scan-import. A
version-1 manifest pins CodeQL 2.27.0, Maven coordinates and every JAR SHA-256 beneath
a local repository root. Missing, extra, changed, symlinked or escaping files are
rejected; coordinates map exactly to the pinned files. Profiles are limited to 1,000
unclassified JAR coordinates and 4 MiB of JSON. scripts/pin_java_dependencies.py pins
pre-provisioned inputs without downloading or overwriting an existing profile.

A generated classpath CSV supplies only file-URI repositories to the pinned CodeQL
standalone extractor. That interface was inspected in the installed 2.27.0 extractor
and verified with real runs; other CLI versions are deliberately not accepted.
Attempt-local dependency scratch is separate from immutable input JARs. Inputs are
reverified after extraction. A mutation results in integrity_failed. Profile identity
is retained in language scope, scan reuse and comparison version 7. No migration.

The container preparation script downloads/verifies six Spring 6.0.10 JARs: web, core,
context, beans, expression and jcl. Maven Central's published SHA-1 values were checked
at provisioning and resulting SHA-256 values are committed in containers/java-profile.json.
These hashes establish pinned bytes, not upstream provenance certification or approval
for bank deployment. This older version reproduces the existing fixture/toolchain;
it is not a recommendation for new production applications.

## Isolation and qualification boundary

The profile alone does not disable CodeQL's inferred dependency fetching. Remaining
unresolved symbols (including the intentional lookalike) still cause attempted remote
fetches in logs. Docker network-none prevents those connections. No network fallback
was enabled and no stub Spring types were added. Reports retain incomplete readiness
and network_denial_verified=false because the app does not attest the external runner.
The runtime probe and container configuration provide separate local isolation evidence.

This qualifies only the exercised annotation/SQL fixtures with the pinned set, not
arbitrary Spring projects, dependency closures, Maven/Gradle builds or deployed endpoint
reachability. Full builds, Linux C# profiles and OCP execution remain open. OCP dev
validation remains deferred until functional POC completion. No live model calls or
bank source were used, and no image was pushed. No user action is required now.

## Validation

Flat Spring acceptance passed all four cases with the profile: vulnerable candidate,
fixed/lookalike zero candidates, incomplete source blocked. Source/sink flow retention
and the narrow advisory evidence gate passed. The earlier web-only profile still
missed the candidate; adding its needed Spring dependencies resolved the fixture.
Final validation: all four Spring cases passed in flat, Maven and Gradle layouts.
Basic Java (two cases) and Python (three cases) also passed in the same restricted
image. 433 regression tests, lint/format checks, CLI help and package/image builds
passed. The pinning helper was exercised against the six-JAR repository.

Image ID: `sha256:1bb9af4803aa9ff8924e0021c1ed7e1ed15222b5f5070ed8f4aca2360c6d29ab`.
The profile ID is `c6d67349ea17f3004d66cf3481ef91cd8b457a414b11612a6a96cbee6a33c71a`.
Results reside under work/slice50-spring-full, work/slice50-spring-maven,
work/slice50-spring-gradle, work/slice50-java-flat and work/slice50-python-flat.
