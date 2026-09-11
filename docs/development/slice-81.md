# Slice 81 — Restricted Linux validation of repaired Joern C#

Outcome: all 20 flow/binding cases passed, all 18 source spans validated, and the seven
source/five sink fact attachments matched expectations. Runtime probes passed. The run
completed in 112.927 seconds; this is not a repository-throughput benchmark.

Added a separate experimental C# qualification image and a joern-csharp container suite.
The image layers on the previously qualified pinned Joern Linux ARM64 base, reinstalls
the current wheel offline, and compiles the isolated frontend class override at image
build time. Original Joern jars remain unchanged. No scanned application is built or
executed; no CodeQL or LLM invocation is required for this suite.

The acceptance suite runs the ten baseline vulnerable/fixed cases and ten adversarial
flow/binding cases, then validates all 18 retained baseline nodes and expected framework
syntax facts. Source nodes may repeat the same parameter; fact counts are not separate
vulnerability counts. Missing, ambiguous or incorrect mappings fail the acceptance run.
All of this remains synthetic bounded qualification rather than broad C# coverage.

Runtime restrictions: Linux ARM64, UID 1000710000:GID 0, read-only root, network none,
all capabilities dropped, no-new-privileges, 2 CPUs, 4 GiB memory, 256 PIDs, bounded
1 GiB /work and /tmp tmpfs, and only the report directory mounted writable from the host.
The existing runtime probe checks denied root writes and network access, with no Docker
socket or service-account token available. Actual OCP SCC/SELinux/PVC behavior is not
established by Docker success.

Recipe: containers/Containerfile.joern-csharp. Suite: containers/joern_csharp_acceptance.py.
Invoke scripts/validate_container.py with --suite joern-csharp and the experimental image.
See the container operator guide for build prerequisites and commands. The derived recipe
uses a local base tag; this run records both immutable IDs. Production registry-digest
packaging and upstream patch qualification remain open rather than relying on tag names.

Artifacts: work/slice81-csharp-linux. These include baseline/binding results, framework
span/fact audit, build receipt, runtime and container configuration/state, tool/package
inventories, logs and validation summary. The final runner uses the inspected immutable
image ID. Source file digests and the one-line patch are checked during the isolated build.
The build uses --network=none with all prerequisites already available locally.

This slice does not register a production C# backend or promote qualified triage. Next
consider a discovery-only experimental C# adapter with explicit coverage and independent
engine evidence gates. Keep broader dispatch, parser completeness, upstream tests/review,
artifact packaging and bank OCP acceptance as open requirements. No migration or user
credentials are needed.

Validated image ID: `sha256:9e9af6eb23ae7658d2a7a30c71323cacb94643e6b8a30dc844fa07cdf3a65be3`.
Base ID: `sha256:d24c591e31121fd5195cb0e0657ce6d98504454f45416022a2c88ff22abb89f8`.
Package build, image build, lint/format and whitespace checks passed. No user action
is needed; changes remain uncommitted.
