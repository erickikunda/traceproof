# TraceProof intake: choose a source and retrieve its report

Current checkpoint: Slice 124. All paths converge on an archive snapshot and explicit
scanner selection. Acquiring source, capturing source, scanning and exporting a report
are separate outcomes. An exported report may still have incomplete security coverage.

| Source supplied by operator | Entry point | Network/identity | Handoff |
|---|---|---|---|
| TAR/ZIP files on mounted PVC | import-csv with archives.csv | No acquisition network or credentials | Captured immutable archive snapshot |
| Git repository CSV | acquire-git-csv with repositories.csv | Allowlisted HTTPS; optional CA/proxy and exact-repository Basic/token file | Successful archives.csv rows plus complete acquisition-batch.json |
| One Git revision | acquire-git | Same Git transport controls | source.zip, input.csv and pinned receipt |
| One GCS archive generation | acquire-gcs | Explicit ADC opt-in; approved bucket; generation and expected SHA-256 | archives.csv and pinned cloud receipt |

Follow the complete commands in the [PVC guide](pvc-archive-intake.md),
[Git batch guide](git-batch-intake.md), [private Git guide](git-private-authentication.md),
and [GCS guide](gcs-archive-intake.md). GCS CSV batching is not implemented; acquire-gcs
accepts one archive. No source filename triggers automatic work.

## Prepare and hand off source

Use a fresh directory per acquisition. Keep operator CA/credential/ADC configuration
outside source and report directories and mount it only into acquisition. Wait for terminal
acquisition status; a killed process can leave an incomplete or running receipt. Never
assume the presence of archives.csv proves all original repositories were acquired.

Preserve archive/receipt hashes. Use the same absolute /handoff mount in both containers
where possible. If moving an output tree, update only CSV source_uri/acquisition_receipt
paths to their new container-visible locations; do not change receipt bytes or digest pins.
Keep repositories.csv outside the offline input root. The offline smoke runner requires
exactly one archives.csv or legacy input.csv and rejects ambiguous input.

For operator-staged archives, use stable repo_id, owner and classification. An expected
archive sha256 is optional for plain PVC input but recommended when supplied independently.
Git and GCS acquisitions produce hash-pinned input. A receipt's binding proves consistency
with captured content; it is not an independently signed assertion of Git/cloud history.

## Run offline and inspect all outcomes

The mounted batch runner handles at most ten CSV rows sequentially with one explicit
language/profile. Divide mixed-language work into appropriate selections. Discovery is
the default, with zero model calls; provider configuration alone does not widen coverage.
Use the [container guide](container-operator-guide.md) and
[OCP manifest guide](../../deploy/openshift/README.md) for runtime commands and limits.

Retain acquisition-batch.json for Git batches and batch.json plus every per-row report
for scanner batches. Failed/unstarted acquisition rows are absent from the success CSV;
a later successful scan must not hide them. Check the report's analysis status, coverage,
source binding and needs_review candidates. Zero candidates is not a clean security verdict.

| Local image inventory | Qualified use at this checkpoint |
|---|---|
| containers/git-acquisition-image.json | Public/private HTTPS acquisition and local HTTP CONNECT acceptance |
| containers/gcs-handoff-images.json | Optional SDK image; synthetic SDK-to-real-offline-C-scan handoff, projection 14 |
| containers/gcs-specialized-images.json | C#/Rust projection 14 vulnerable/fixed GCS handoff acceptance |
| containers/ocp-smoke-images.json | Prior general/C#/Rust image pairings; Git/plain-archive projection 13 acceptance |

Image tags are mutable. Select the tested digest pairing in the inventories, not an assumed
latest checkout. The GCS general scanner image packages seven language selections, but the
new GCS handoff was exercised only with C. Separate C#/Rust GCS image tags now have projection 14 vulnerable/fixed handoff acceptance. Real cloud, bank identity and OCP acceptance remain pending.

## Retrieve and share

For durable local CLI state, use report-history REPO_ID to find the report ID, then:

```sh
traceproof --state-dir /path/to/state get-report REPO_ID --report-id REPORT_ID --format html
traceproof --state-dir /path/to/state get-report REPO_ID --report-id REPORT_ID --format scan-csv
traceproof --state-dir /path/to/state get-report REPO_ID --report-id REPORT_ID --format json
```

Exact retrieval does not scan or invoke models. JSON is canonical; HTML is readable and
CSV is a dashboard projection. Keep report ID, source identity and coverage with shared
results. HTML and source evidence may be sensitive; operator file access is the current
boundary, not hosted authorization. There is no hosted HTTP API today.

Offline smoke jobs use disposable SQLite/artifact scratch and persistent report output.
Their exported reports survive, but they do not provide a persistent report-query service
once scratch disappears. Archive those exports deliberately. Redis is not required for this
POC; shared SQLite on PVC is not a substitute for future PostgreSQL multiworker orchestration.
