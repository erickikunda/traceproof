# Operator-staged PVC archive batches

This input path already works through the existing CSV/archive intake. The operator copies
the CSV and source archives to a PVC; VeriFlow reads them through its mounted input folder.
No Git connectivity or credentials are needed.

## Naming convention

- **archives.csv** — source paths to operator-supplied TAR, TAR.GZ or ZIP archives.
- **repositories.csv** — Git-URL acquisition batches, processed explicitly with acquire-git-csv
  (Slice 114); network acquisition remains separate from offline archive intake.

Use a separate batch directory for each submission; the directory supplies the batch name:

```text
/input/batch-001/
  archives.csv
  archives/
    payments-api.zip
    customer-service.tar.gz
```

Example archives.csv:

```csv
repo_id,source_type,source_uri,owner,classification
payments-api,pvc,/input/batch-001/archives/payments-api.zip,payments,internal
customer-service,pvc,/input/batch-001/archives/customer-service.tar.gz,customer-platform,internal
```

source_uri must be an **absolute path visible inside the application container**, beneath
the configured input root. It is not a laptop path or PVC resource name. source_type is pvc.
The optional sha256 column can pin each archive's bytes. repo_id is the logical repository
identifier; filenames do not determine identity. Up to 1,000 rows are supported per CSV.

The current importer accepts an explicitly supplied CSV filename; naming alone does not
select behavior or trigger scanning. No folder watcher or automatic Git/archive routing is
claimed. Existing CSV schema and archive validation remain authoritative.

## Submit and process

After copying all files, stop modifying the batch before admission. Stage under a temporary
batch-directory name and rename it when copying finishes, where the storage supports that
operation. Mount input read-only in the application. Use the established local/ephemeral
state arrangement; do not place shared SQLite state on the input PVC.

```sh
veriflow --state-dir /work/state init
veriflow --state-dir /work/state import-csv /input/batch-001/archives.csv \
  --input-root /input/batch-001 --key batch-001
veriflow --state-dir /work/state worker IMPORT_ID
veriflow --state-dir /work/state import-status IMPORT_ID
```

Use the returned import ID. Intake snapshots the archives; it does not itself perform a
security scan. Continue with the existing scan-import or scan-run workflow, explicitly
selecting the scanner/language/profile and appropriate toolchain image. Check per-row
status: a partially accepted batch must not be interpreted as every repository scanned.
For mixed-language batches, scanner/profile selection is still an explicit scan concern;
the CSV filename does not perform per-row model selection.

## Current smoke-Job distinction

The narrow OpenShift smoke entrypoint now accepts **/input/archives.csv** or legacy
**/input/input.csv**, but never both. It rejects repositories.csv because that is a
network-acquisition input, not an offline archive manifest. Missing, linked and non-file
manifests fail before scan state is created. The selected filename is recorded in result.json.

This demonstration still accepts exactly one row. The existing general CLI import-csv/worker
supports multi-row batches; a separate mounted batch entrypoint now supports up to ten rows per Job (Slice 111).
Render with --batch-max-rows N and one explicit language/profile; over-limit CSVs are rejected
without truncation. See the deployment guide for per-row exports, mixed-failure exit status
and disposable-state limits. Actual bank OCP execution remains deferred.
