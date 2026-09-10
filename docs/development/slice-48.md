# Slice 48: restricted Linux image and local Python acceptance

Slice 47 was committed as 3e22044. This slice begins the required OCP preparation track.
Per user direction, real bank OCP testing is deferred until the functional POC is
complete; preparation and local validation proceed now.

Implemented a digest-pinned UBI9 Python 3.12 container with hash-locked Python runtime
dependencies and checksum-pinned CodeQL 2.27.0 Linux ARM64/query bundle. An allowlist
.dockerignore limits the build context and excludes state, .env files and unrelated
work artifacts. scripts/build_container.py verifies downloads and builds a wheel/image;
scripts/validate_container.py runs the immutable local image ID in a restricted container.

Runtime: arbitrary non-root UID, no capabilities or privilege escalation, read-only
root filesystem, no external network, bounded CPUs/memory/PIDs and writable scratch.
The real Python vulnerable/fixed/incomplete suite checks detection, blocked incomplete
input, report exports and exact report retrieval without model calls. Probe evidence,
container config/state, package inventories and report artifacts are exported locally.
No database migration or cluster access is needed. No image was pushed.

The first real container run passed all three cases in 19.764 seconds. This is functional
fixture evidence only, not fleet throughput. No OCP SCC/SELinux/CNI admission is claimed.
Final validation uses the completed recipe and is recorded with its immutable image ID
under work/slice48-container-final. See the container operator guide for reproduction.

Scope still open: Linux Java/C# toolchains, AMD64, formal SBOM/signing, OCP manifests,
PostgreSQL durability and stage isolation. The image includes CodeQL extractors but
only Python container acceptance is qualified here. No bank source or live model calls.

[Container operator guide](../guides/container-operator-guide.md)

Final validation passed in 19.194 seconds using image
`sha256:f28c40b9194e98bfa98c98cfb4927d9e0a76e8dceba1753be57759fa35008804`. All three cases and runtime probes passed;
421 regression tests, Ruff lint/format checks and package/image builds passed.
A negative runtime check rejected root execution. No migration.
