# GCS archive acquisition

Install the optional acquisition dependency with `uv sync --extra gcs`. The base/offline
scanner does not need this dependency. Operator-provisioned Google Application Default
Credentials (ADC) must already be configured in the acquisition environment. --use-adc
explicitly opts into ADC discovery; TraceProof does not run login or create keys. In OCP,
use the bank-approved identity mechanism and mount configuration only into acquisition.

```sh
traceproof acquire-gcs approved-input folder/source.zip 123456789 EXPECTED_SHA256 \
  /handoff/new-gcs-source repo-id team classification \
  --allowed-bucket approved-input --use-adc --timeout 300
```

Replace generation and SHA-256 with trusted operator-supplied values. Bucket, object and
generation are separate arguments, not an arbitrary URL. The default maximum archive is
100 MiB, configurable to at most 1 GiB. Supported suffixes are .zip, .tar, .tar.gz and .tgz.
The output directory must not exist. Successful output contains source archive, archives.csv
and acquisition.json. Feed archives.csv into existing offline intake with the same absolute
mount path. Inspect the terminal receipt first. Acquisition does not unpack, scan or invoke
models; malformed archive contents can still be rejected by downstream intake.

Both metadata and ranged downloads specify the generation and if_generation_match.
Raw download avoids transparent content decoding; total size and expected SHA-256 are
verified before publishing the CSV. Ranges are 1 MiB, storage retries are disabled, and each
request receives at most 30 seconds or the remaining workflow budget. ADC refresh/discovery
and SDK/socket behavior are not a hard process wall-time bound: enforce a job deadline,
CPU/memory and volume limits in deployment. The SDK can buffer a response before range-size
validation; do not treat chunk size as a hard memory quota.

ADC may discover local credentials or contact approved identity/metadata services. Operator
configuration is trusted; it must not come from scanned repositories. Live emulator endpoint
overrides are rejected. Standard SDK proxy/CA/identity behavior is separate from the explicit
Git transport settings and requires bank validation. GCS source metadata is retained in a digest-pinned, repository-bound receipt. Intake persists
it and verifies archive hash/size against the captured manifest. Projection 14 reports
bucket/object/generation and admitted versus snapshot_bound state. This binds archive
content, not independent cloud history. No Git commit identity is invented.

Current tests mock the SDK boundary and verify pinned metadata/range calls and failure
handling. No real GCS access, bank identity, OCP run or cloud cost qualification has occurred.
Existing container images do not include the optional SDK or this new command; acquisition
packaging remains follow-up work; durable GCS provenance is implemented in Slice 121. No bucket mutations or listing are
performed by this command.

SDK behavior reference: [Google Blob API](https://docs.cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.blob.Blob).

## Container packaging (Slice 122)

A dedicated image now includes the optional SDK, using containers/requirements-gcs.lock:

```sh
uv build
docker build -f containers/Containerfile.gcs-acquisition -t traceproof:gcs-acquisition-linux-poc .
docker build -f containers/Containerfile.ocp-smoke -t traceproof:ocp-smoke-gcs-linux-poc .
uv run python scripts/validate_gcs_handoff.py work/new-gcs-handoff
```

The acquisition entrypoint is acquire-gcs; pass its arguments as in the example above.
Provide operator-approved ADC configuration only to acquisition, mount input configuration
read-only, and write archives/receipts to the handoff PVC. Mount the same handoff path
read-only into scanning. No cloud credential belongs in the offline scanner container.

The local rehearsal replaces SDK responses with synthetic archive bytes and then performs
a real offline C scan. It verifies report projection 14 with snapshot-bound cloud provenance.
It does not access Google services. Exact images and input hashes are recorded in
containers/gcs-handoff-images.json. Slice 124 supplies separate GCS-compatible C#/Rust images with vulnerable/fixed handoff
acceptance. See containers/gcs-specialized-images.json; older smoke tags are unchanged.


Specialized validation uses --language csharp or --language rust and --case vulnerable/fixed
on scripts/validate_gcs_handoff.py. Build the matching Containerfile.ocp-smoke-csharp or
Containerfile.ocp-smoke-rust with tag traceproof:ocp-smoke-gcs-csharp-linux-poc or
traceproof:ocp-smoke-gcs-rust-linux-poc first. Use a new output directory for every case.


## Whole-language local acceptance (Slice 125)

validate_gcs_handoff.py now accepts all nine language selections and both existing fixture
cases. For each general language (java, python, javascript, typescript, go, c, cpp), run it
with --language LANGUAGE --case vulnerable and --case fixed using separate output folders.
C#/Rust use their specialized tags. These are real offline scans after mocked SDK acquisition.

summarize_gcs_acceptance.py accepts the 18 validation.json paths and emits a combined JSON
matrix. Missing or duplicate pairs, wrong counts, cloud/model calls or image mismatches
within a pair are errors. Recorded matrix: containers/gcs-acceptance-matrix.json. No real
cloud service or model judgment is tested by this matrix; all reports retain incomplete
coverage. Retain the referenced work artifacts separately if needed; work/ is not committed.
