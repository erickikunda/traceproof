# Local Linux container operator guide

This is the first OCP preparation image, qualified locally for synthetic Python
scan acceptance on Linux ARM64. It is not an OCP-certified deployment. No OpenShift
installation is needed on the laptop. Docker Desktop and uv are required for the
following commands; run from the TraceProof checkout.

## Build

```sh
uv run python scripts/build_container.py
```

Preparation downloads the checksum-pinned CodeQL 2.27.0 Linux ARM64 bundle into ignored
work/container-inputs, builds the application wheel and builds traceproof:linux-poc.
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
or executable is copied into the image. Java/C# runtime/toolchain qualification is a
subsequent slice; bundled extractors alone do not establish language readiness.

## Run acceptance

```sh
uv run python scripts/validate_container.py work/container-acceptance-001
```

The output directory must be new. The test runs the inspected immutable image ID with:

- Arbitrary non-root UID 1000710000, group 0; all capabilities dropped.
- Read-only root filesystem, no-new-privileges, Docker default seccomp.
- No external network (`--network none`), no Docker socket or model credentials.
- Two CPUs, 4 GiB memory, 256 PIDs, bounded stage and overall timeouts.
- Separate tmpfs scratch for /work and /tmp; /reports binds only the new output directory.

Runtime probes check the applied process privileges, denied writes and external network
failure. Network-none retains loopback; it does not forbid communications within the
same container. The Python vulnerable/fixed/incomplete acceptance then runs real CodeQL
extraction/querying and exact report retrieval. SQLite state is temporary in /work;
this is deliberately not durable/shared-database qualification. Reports survive on the
host; state/databases disappear with the container. Execute permission on scratch is
needed for toolchain operation; no hostile source builds are enabled by this recipe.

The script removes only its own randomly named container. On failure it preserves CLI
output, container state and available extractor/query logs. A hard kill/OOM may prevent
log export from tmpfs; container-state.json records the runtime outcome. No background
services are started. A failed acceptance exits nonzero.

Outputs include validation.json, runtime.json, acceptance.json, per-case JSON/HTML/
Markdown/CSV reports, image/runtime configuration, Python package inventory and RPM
package inventory. Inventories are not a formal SPDX/CycloneDX SBOM. Treat diagnostic
logs and reports as source-sensitive when adapting this workflow to real repositories.
The roughly 20-second synthetic first run is not a throughput benchmark.

## OCP preparation boundary

RHCOS is the node OS; dependencies belong in the image, approved volumes or service
endpoints. Do not mount host paths or Docker sockets into future worker pods. In OCP,
let the SCC assign the UID rather than copying this test UID into pod manifests.

Remaining work: Linux Java/.NET dependency profiles and fixtures; matching bank CPU
architecture; namespace Job/NetworkPolicy/PVC manifests; SELinux/SCC admission; corporate
CAs/mirrors; stage-separated egress and credentials; PostgreSQL durability; formal image
SBOM/signing/scanning; and finally the bank OCP smoke test. Actual cluster testing is
scheduled after functional POC completion. Local Docker success does not satisfy it.

The current --csharp-offline option uses macOS sandbox-exec and intentionally rejects
Linux. OCP/Docker isolation must be integrated as a distinct runner mode; do not pass
that flag inside this image or falsely report platform-enforced isolation as macOS
verification. LLM calls remain untested in this network-disabled acceptance run.
