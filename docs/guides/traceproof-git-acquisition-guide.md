# Public Git URL acquisition


`acquire-git` prepares one source archive and CSV; it does not initialize a scan database,
scan source or invoke a model. Git must be installed. Only credential-free HTTPS on explicitly
allowed hosts is accepted. Use an immutable 40-character commit when available; full branch
or tag refs are resolved once and the resulting commit is recorded.

```sh
veriflow acquire-git https://github.com/octocat/Hello-World.git refs/heads/master \
  /absolute/work/acquired-repo hello-world poc public --allowed-host github.com
```

The output directory must not exist. Parameters after the revision are output directory,
repository ID, owner and classification. Repeat --allowed-host for an operator-approved host
list; --timeout defaults to 300 seconds (maximum 900). URL usernames/passwords, query tokens,
SSH/file URLs and redirects are unsupported. Personal Git configuration, credential helpers,
proxy and custom CA environment are not inherited. Private/corporate configuration is not
implemented yet; do not work around this by embedding credentials in the URL.

After successful completion, inspect acquisition.json and require state=acquired. Keep its
resolved_commit, archive_sha256 and per-file hashes with the exported source. The generated
input.csv points to the absolute source.zip path and declares its hash. Submit that CSV with
the existing import-csv command, using the acquisition directory as input-root, then follow
the normal worker and scan workflow. The initial CSV source_type is still pvc;
putting a Git URL directly in ordinary import-csv is not supported.

When moving the output to a PVC/container, update only the CSV archive path to its absolute
mounted location (for example /input/source.zip); preserve the SHA-256 value. The smoke Job
still consumes exactly one archive row. Do not run networked acquisition inside the offline
scanner Job or add credentials to its manifest. Current reports do not embed the Git sidecar;
retain both artifacts for traceability until provenance integration is implemented.

Export reads raw blobs, preserving files marked export-ignore and bypassing checkout filters.
Symlinks, submodules and LFS pointers are rejected, as are file/path/size limits. Limits are
2,000 files, 5 MiB/file, 100 MiB source and a monitored 256 MiB temporary Git workspace.
Workspace monitoring can overshoot and is not an OS quota. Failure yields no usable CSV;
inspect acquisition.json and retry into a fresh directory after resolving the cause. Forced
termination can leave an incomplete directory; never consume it without a successful receipt.
