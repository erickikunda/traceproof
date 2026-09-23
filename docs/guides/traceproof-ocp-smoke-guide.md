# Offline OCP smoke Job — Slice 106

This is a **single-archive, explicitly selected discovery-profile smoke test**, with disposable SQLite
and zero model calls. It prepares OCP-2; it is not a multiworker deployment, complete language-coverage
image or evidence of OCP acceptance. The local image is ARM64 and its Job selects ARM64
nodes. Do not remove that selector to pretend AMD64 is qualified.

## Language selections (Slices 107–108)

Select one language per Job with `--language` on the renderer. The entrypoint uses the
image-specific packaged allowlist; repository metadata cannot select tool paths or arbitrary queries.
C remains the general image default; specialized images default to their sole language.
There is no auto/mixed-language expansion. A language absent from the selected image
is rejected before creating scan state. The renderer accepts the union of these selections,
but cannot authenticate which image a supplied registry digest contains.

| Selection | Packaged discovery profile |
|---|---|
| java | default Spring/JDBC |
| python | python-flask-system-v1 |
| javascript | express-request-eval-v1 |
| typescript | express-request-eval-v1 |
| go | go-http-shell-v1 |
| c | c-family-argv-system-v1 |
| cpp | c-family-argv-system-v1 |
| csharp (specialized image) | default repaired Lookup/CommandText |
| rust (specialized image) | rust-env-shell-v1 |

C# needs the qualified repaired frontend image and Rust needs its separate UBI/toolchain
image. Their existing local scanner support is unchanged; this smoke image does not contain
those toolchains. Specialized recipes below provide them. No advisory policies or model
calls are enabled in these Jobs.

## Build and rehearse on the laptop

The digest-pinned base is the local Slice 104 Joern advisory image. It must already exist;
its build recipe is containers/Containerfile.joern-argv-advisory. As of Slice 113, the smoke
layer preserves the pinned toolchain but installs the current built wheel and hash-locked
Python requirements. Run uv build before docker build; an old dist wheel is not automatically
refreshed. Requalify images after application or toolchain changes.

```sh
uv build
docker build -f containers/Containerfile.ocp-smoke -t veriflow:ocp-smoke-linux-poc .
uv run python scripts/validate_ocp_smoke.py --image veriflow:ocp-smoke-linux-poc --language python work/ocp-smoke-rehearsal
```

Use a fresh output directory. The runner supplies synthetic vulnerable/fixed ZIP inputs,
probes restricted runtime settings and executes the real image entrypoint. It checks
candidate counts 1/0, exact report IDs, partial coverage and zero calls. Docker mounts
/input read-only; /reports is the export mount; /work and /tmp are disposable writable
scratch. Joern requires executable scratch for native tool loading; noexec scratch fails.
The host report-directory permission used by this Docker Desktop harness is not a bank
PVC permission prescription. Docker tmpfs resource accounting also differs from OCP's
disk-backed emptyDir; the rehearsal is not storage/capacity qualification.

## Specialized C# and Rust images (Slice 108)

```sh
docker build -f containers/Containerfile.ocp-smoke-csharp -t veriflow:ocp-smoke-csharp-linux-poc .
uv run python scripts/validate_ocp_smoke.py --image veriflow:ocp-smoke-csharp-linux-poc --language csharp work/ocp-csharp-rehearsal
docker build -f containers/Containerfile.ocp-smoke-rust -t veriflow:ocp-smoke-rust-linux-poc .
uv run python scripts/validate_ocp_smoke.py --image veriflow:ocp-smoke-rust-linux-poc --language rust work/ocp-rust-rehearsal
```

Run sequentially with fresh output directories. As of Slice 113 all three smoke variants
install the same current wheel/locked Python dependencies over their distinct pinned scanner
toolchain bases. C# retains its repaired frontend and Rust its UBI 10/toolchain. This updates
application behavior without rebuilding or widening the underlying language models.
Run uv build first and requalify the resulting images. Rust preparation retains the strict
dependency-free Cargo contract; no repository build hooks or runtime package downloads are added.

C# supplies the fixed /opt/veriflow/csharp-repair directory to the shared scanner, which
checks repair identity. Rust supplies /opt/rust to the existing toolchain validator and
retains UBI 10. C# remains the bounded repaired Lookup source profile; the smoke fixture
uses ASP.NET Core, not qualification of every ASP.NET API. Both exports remain incomplete.

Render with `--language csharp` or `--language rust` and the corresponding mirrored image
digest. Pairing a specialized language with the general image fails selection. Supplying a
specialized image for an unrelated language likewise fails. Do not try to supply repair or
Rust paths through CSV metadata. Selection and tool validation failures do not fall back
to another engine or profile. All these images are ARM64; target-bank architecture is open.

## Prepare bank input and render (no cluster access required)

Prepare separate existing input/report PVCs through the bank's storage process. The input
PVC must contain archives.csv and source.zip (or a supported tar archive). CSV example:

```csv
repo_id,source_type,source_uri,owner,classification
synthetic-repo,pvc,/input/source.zip,poc,synthetic
```

Exactly one PVC archive row is accepted. The archive must contain the selected language's source files; its
path is the container path, not a laptop path. Existing safe archive/CSV intake validation
still applies. The source input is read-only; SQLite stays in /work, never the report PVC.

After approved image mirroring, use the **destination registry's verified digest**, not a
local image config ID. The checked-in smoke.example.json uses a deliberately nonexistent
registry hostname; it is review material, not ready to deploy.

```sh
uv run python scripts/render_ocp_smoke.py \
  --namespace veriflow-dev --name veriflow-smoke --language python \
  --image "$APPROVED_IMAGE_WITH_SHA256_DIGEST" \
  --input-pvc veriflow-input --reports-pvc veriflow-reports \
  --output work/ocp-smoke.json
```

The renderer emits a namespaced ServiceAccount, selected-pod ingress/egress deny policy
and Job. It makes no network calls, creates no PVC/namespace and grants no Roles. Token
automount is disabled. The Job has one completion, no automatic retry, a 600-second
deadline, CPU/memory/ephemeral-storage limits, read-only root, dropped capabilities and
no privilege escalation. UID and fsGroup are intentionally left for SCC/storage admission.
[OpenShift SCC guidance](https://docs.redhat.com/en/documentation/openshift_container_platform/4.16/html/authentication_and_authorization/authentication_and_authorization)
and [Kubernetes Job controls](https://kubernetes.io/docs/concepts/workloads/controllers/job/).

NetworkPolicies are additive: another matching allow policy can permit egress. The bank
must verify effective policy and enforcement by its network plugin; this manifest alone
is not proof of isolation. Image pulling is performed outside pod egress policy. There
are no LLM secrets in this Job.
[Kubernetes NetworkPolicy behavior](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

## Later cluster acceptance — not performed here

A platform operator should review the rendered file, confirm registry pulls, ARM64 node
availability, SCC admission, executable scratch and read/write SELinux/PVC permissions,
then perform server-side validation before applying it to the approved namespace:

```sh
oc apply --dry-run=server -f work/ocp-smoke.json
oc apply -f work/ocp-smoke.json
oc -n veriflow-dev wait --for=condition=complete job/veriflow-smoke --timeout=620s
oc -n veriflow-dev logs job/veriflow-smoke
```

A timeout may mean failed, pending, evicted or deadline-exceeded work. Inspect Job/Pod
status and events; do not treat a wait timeout as a diagnosis. Record the admitted SCC,
image digest, architecture, resource outcomes, enforced egress and storage behavior.
No oc commands were executed during local validation. No server schema/admission check
or cluster compatibility is claimed by local configuration tests.

## Manifest names (Slice 110)

Use /input/archives.csv. Legacy /input/input.csv is accepted only when archives.csv is absent.
Having both is an error, even if their contents match. repositories.csv is rejected, alone
or alongside an archive manifest, to prevent silently ignoring a Git batch. Linked/non-file
manifests are rejected by the existing scoped file opener. Selection errors occur before
scan state creation and yield the usual failure record when report storage is writable.
result.json includes manifest_name after successful selection; it is absent for ambiguity.

The default rehearsal now writes archives.csv. To exercise compatibility, add
`--manifest-name input.csv` to scripts/validate_ocp_smoke.py and use a fresh output directory.
The single-row limit remains; the general CLI worker is the existing multi-row interface.

## Reports, failure and retry

Outputs are /reports/<pod-UID>/report.json, report.html and result.json. Pod UID comes
from the downward API without API permissions. Directory creation is exclusive: an
existing execution ID cannot overwrite earlier exports. Keep the exact report_id in
result.json for reference; the exported JSON is the corresponding immutable projection.
The ephemeral database disappears with the pod, so later database-backed retrieval is
not available from this smoke run. Archive the exports through approved storage tooling.

Exit 0 means the smoke workflow exported a partial discovery report, **not a clean scan**.
Review readiness remains incomplete even for zero candidates. Failed analysis exports
available reports, marks result.json failed and exits nonzero. Other exceptions emit a
sanitized error type; writable exports are required to persist the failure record.
Diagnostics retain at most 16 log prefixes of 1 MiB each and may contain source text.
Treat report storage as sensitive; no retention cleanup is automated. SIGKILL, OOM or
pod deadline termination can leave incomplete/missing exports because finally handlers
cannot be guaranteed. Inspect pod status and preserve partial output.

A rerun requires a new Job name/rendered file and receives a new pod UID. It rescans;
there is no cross-pod exactly-once or restart durability guarantee. Kubernetes may create
replacement pods in unusual conditions even for a single-completion Job; unique export
paths avoid overwrites, but do not deduplicate work. Operators own cleanup of old Jobs,
ServiceAccounts, NetworkPolicies and exports after retaining required evidence.

## Next scope

Bank platform architecture/registry/storage/SCC information is needed before deployment,
not before local development. Next address remaining input-acquisition gaps, starting with repository URLs, keeping this smoke contract distinct from multiworker PostgreSQL/Redis and
credential-bearing triage. Actual OCP execution remains deferred as agreed.

## Mounted multi-row batches (Slice 111)

The images now also contain /opt/veriflow/ocp_archive_batch.py. Select it explicitly through
`--batch-max-rows N` on scripts/render_ocp_smoke.py, with N from 1 to 10. Without this option,
the original one-row smoke entrypoint remains selected. Batch mode uses the same image-specific
language/profile selection; all repositories in a Job are scanned with that selected profile.
Separate batches by language/toolchain; there is no per-row automatic routing.

```sh
uv run python scripts/render_ocp_smoke.py \
  --namespace veriflow-dev --name veriflow-archive-batch --language c \
  --image "$APPROVED_IMAGE_WITH_SHA256_DIGEST" \
  --input-pvc veriflow-input --reports-pvc veriflow-reports \
  --batch-max-rows 3 --output work/ocp-archive-batch.json
```

Stage archives.csv with one row per repository and all referenced archives under /input.
Legacy input.csv and ambiguity rejection follow the same rules as smoke mode. A CSV exceeding
the requested limit is rejected as a whole before intake; there is no silent truncation.
The core CLI still supports larger batches; this mounted Job deliberately caps its work.

The renderer sets the Job deadline to N × 360 + 300 seconds, retaining single-pod execution,
no automatic Job retries and the existing CPU/memory/storage/security settings. The time
allowance is not a throughput guarantee. Total scratch usage can still exhaust the fixed
volume/resource limits; split large inputs. SQLite and internal artifacts remain disposable.

Outputs under /reports/<pod-UID>/:

```text
batch.json
row-000002/report.json
row-000002/report.html
row-000004/report.json
row-000004/report.html
```

Rows use physical CSV data-row numbering (first data record is row 2); numbers refer to
records, not embedded-newline physical lines. batch.json lists every data record's state,
intake state, run/report IDs where available, candidate count and relative JSON report path.
Row-directory names prevent duplicate repository labels from overwriting one another.
The summary is replaced atomically before scanning and after each completed row; this is a
progress export, not a durable restart/checkpoint protocol or an fsync guarantee.

A ready row is scanned through the existing bounded scan-import page of one. Rejected/failed
intake rows become intake_not_ready and later rows continue. Expected scan errors remain
scan_failed; not-dispatched rows are explicit. Infrastructure exceptions stop the batch,
record a sanitized error type and preserve pending/scanning states for uncompleted work.
The batch summary does not export raw intake error text or scanner logs; retain pod events
and inspect available reports. Kill/OOM/deadline termination can leave a running summary;
correlate with Job status instead of treating it as successful work.

Exit 0/state=exported requires every row to export a report with partial analysis status.
This still means incomplete security coverage, never a clean verdict. Any row that cannot
qualify makes state=incomplete and exit 1, while retaining successful exports. Unexpected
exceptions make state=failed/exit 1. No automatic fallback, model calls or Git retrieval.
Use a new Job name for a fresh attempt; state is not shared across Jobs and duplicate work
is possible. Preserve earlier exports before cleanup.

Local batch rehearsal (fresh output directory, run images sequentially):

```sh
uv run python scripts/validate_ocp_archive_batch.py --image veriflow:ocp-smoke-linux-poc --language c work/batch-c
uv run python scripts/validate_ocp_archive_batch.py --image veriflow:ocp-smoke-csharp-linux-poc --language csharp work/batch-csharp
uv run python scripts/validate_ocp_archive_batch.py --image veriflow:ocp-smoke-rust-linux-poc --language rust work/batch-rust
```

Each rehearsal scans a vulnerable/fixed two-row batch, then a three-row batch with a missing
archive between the valid rows. The latter must exit nonzero and still export both valid
reports with 1/0 candidate counts. This is synthetic local Docker acceptance, not actual OCP
storage/network/admission or representative bank performance qualification.


## Receipt-enabled images and build identity (Slice 113)

All three refreshed variants accept acquisition_receipt/acquisition_sha256 CSV columns and
publish report projection 13. The runtime remains offline: a receipt is staged with its
archive and both paths must be beneath the input root. The image does not re-fetch Git.
Plain archive CSVs continue to work and publish null acquisition_provenance.

The build performs pip check and records SHA-256 values for the installed input wheel and
requirements.lock at /opt/veriflow/application-inputs.sha256. The local qualification
inventory is containers/ocp-smoke-images.json. Its identities describe the exact tested
artifacts, not arbitrary future tags. This is a build-input inventory, not a full SBOM or
signed supply-chain attestation. Mirroring to a bank registry requires checking destination
digests and bank approval as before. No image has been pushed by this slice.

For receipt acceptance use scripts/validate_ocp_archive_batch.py with --provenance. This
creates explicitly synthetic receipt metadata, validates valid snapshots and tampers one
receipt in a mixed batch. Expected behavior: tampered row rejected, later valid row exported,
nonzero mixed-batch exit and snapshot_bound provenance on the valid reports. Synthetic Git
commit assertions are not authenticated remote history. The plain mode still tests a missing
archive, with null provenance on valid rows. Both modes should pass after a refresh.
