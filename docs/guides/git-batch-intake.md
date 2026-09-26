# Git-URL CSV acquisition

Use **repositories.csv** for networked Git acquisition and **archives.csv** for offline
archive intake. These are operator conventions; filenames do not trigger automatic work.
The explicit command chooses the operation. Both paths remain independent: staging archives
on a PVC does not require Git connectivity or credentials.

## Input and execution

```csv
repo_id,url,revision,owner,classification
hello-world,https://github.com/octocat/Hello-World.git,refs/heads/master,poc,public
```

These five columns are required; archive-only fields and arbitrary Git options are not
accepted here. Use a full refs/heads or refs/tags revision, or a 40-character commit.
URLs must be credential-free HTTPS with no redirects. Hosts are approved explicitly at
invocation, never supplied by CSV metadata. Existing acquisition restrictions apply to
each row: no inherited credentials/proxy/custom CA config, submodules, LFS or
symlink content; no checkout, build, scanner or model execution.

```sh
veriflow acquire-git-csv /staging/repositories.csv /staging/acquired-batch \
  --allowed-host github.com --max-rows 10 --timeout 900
```

The output directory must not exist. Maximum row count is 1–10, default ten. The batch
acquisition deadline defaults to 900 seconds, configurable from 1–3600. Each row receives
at most 300 seconds and no more than the remaining batch time. Existing per-acquisition
size/process limits still apply. Cleanup/output operations may extend elapsed wall time;
use OS/container quotas for hard resource isolation. Successful retained archives accumulate
across rows, so reserve storage for the whole batch, not just one temporary clone.

## Output and partial failure

```text
acquired-batch/
  acquisition-batch.json
  archives.csv
  row-000002/
    source.zip
    acquisition.json
    input.csv
  row-000004/
    source.zip
    acquisition.json
    input.csv
```

acquisition-batch.json accounts for every CSV record, with record numbers starting at 2.
It includes input-manifest SHA-256, per-row states, exact commit/archive identity for successes
and the number of archive entries produced. Invalid-row values are not copied into the
summary; expected errors are sanitized application messages. Source row numbers identify
failures without exposing rejected credential-bearing URLs.

archives.csv contains **successful acquisitions only**, including receipt paths and pinned
receipt/archive hashes. If none succeeds, no archives.csv is published. Per-row errors do
not block later valid rows. Once the deadline is exhausted, remaining rows are not_started;
infrastructure exceptions stop processing and preserve pending/acquiring states.

Exit 0/state=acquired means every row was acquired, not scanned. Partial failure or deadline
returns state=incomplete/exit 1; unexpected infrastructure errors return exit 1. Outputs are
checkpointed using atomic file replacement, not a cross-file transaction or fsync/restart
guarantee. Kill/OOM can leave a running summary. **Wait for a terminal result and inspect all
rows before consuming archives.csv.** Retain acquisition-batch.json with downstream reports;
a successful scan of the success subset does not mean the original full batch completed.

Existing output is never overwritten. Retry failed rows deliberately into a fresh batch;
there is no automatic retry or durable resume. Repeating a moving branch can resolve to a
new commit; use recorded commits for an intentional pinned repeat.

## Offline handoff

Submit generated archives.csv through the existing import-csv/worker/scan workflow, with the
acquisition output directory as input-root. Durable receipt binding is preserved. When moving
to a PVC, copy the output tree, then update source_uri and acquisition_receipt to absolute
container-visible paths; preserve archive/receipt digest fields and relative subdirectories.
Keep repositories.csv outside the offline Job input root because that Job rejects Git input.

No scans are started by acquisition. A mounted batch scan uses one selected language/profile
and the appropriate qualified image. The raw generated success CSV can span languages;
partition it intentionally before dispatching profile-specific Jobs. Automatic per-row
language/image routing is not implemented here.

This command is available from the local checkout and the separate acquisition image
(Slice 115). The pinned offline scanner images are not a networked acquisition service. Private Basic/token and explicit CA/proxy options are implemented. Corporate infrastructure
and actual OCP acceptance remain pending; GCS uses its separate acquire-gcs path. An allowed hostname is not an OS-level egress isolation guarantee.

## Explicit CA and proxy options (Slice 116)

Both acquire-git and acquire-git-csv accept operator options:

```sh
veriflow acquire-git-csv /staging/repositories.csv /staging/new-batch \
  --allowed-host git.example.invalid \
  --ca-bundle /config/corporate-ca.pem \
  --proxy http://proxy.example.invalid:8080
```

The bundle must contain PEM CA certificates and be at most 1 MiB. Provide the complete
required trust bundle; do not assume it appends to system trust. The same bundle is used
for TLS to an HTTPS proxy. TLS verification stays enabled. Proxy URLs accept HTTP or HTTPS,
an optional port, and no credentials, query or non-root path. These settings are not CSV
columns and are never inferred from environment variables. Keep the operator configuration
mount read-only and stable across the batch. Each acquisition copies validated CA bytes
into its private scratch directory; configuration is not included in archive provenance.

Private Git Basic/token credentials are supported through an exact-repository file; see [private authentication](git-private-authentication.md). Authenticated proxies remain unsupported. No live corporate
proxy/CA acceptance has been performed. The Slice 118 acquisition image includes these options and has local smart-HTTP and HTTP CONNECT acceptance. The offline scanner needs neither
option nor access to this configuration mount.
