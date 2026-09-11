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
