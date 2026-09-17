# Slice 147 — Networked OSV export acquisition

Added `osv_acquisition.py`, `osv_reader.py`, the `acquire-osv` command,
`containers/Containerfile.osv-acquisition` and `scripts/validate_osv_acquisition.py`. Acquisition
produces exactly the pinned export `get-osv` and `get-sbom --database` already verify, so the
offline matcher is unchanged and still never opens a socket.

The split follows the GCS contract: `osv_acquisition.py` holds every gate against an
`ExportReader` protocol and `osv_reader.py` is the only networked component. The source must be
credential-free HTTPS on an explicitly allowed host, with no query, fragment, credentials,
non-default port or parent traversal. Redirects are refused outright because a redirect could
leave the validated host. Proxy and CA settings come from `git_transport.transport_settings` and
environment proxy discovery is disabled.

An unexpected archive member aborts the whole acquisition rather than being skipped: nested
paths, non-JSON names, hidden names and non-regular entries are all refused. A silently
incomplete database would later be reported as fully evaluated, which is the failure this stage
exists to prevent. Per-record size, total expanded bytes, record count and compression ratio are
bounded. An advisory shipped in several ecosystem archives is written once when the bytes agree
and refused when they disagree; `build_index` gained a matching duplicate-id guard so a
hand-built export cannot report one advisory twice.

Freshness cannot be pinned the way a commit or a generation can, because the OSV export has no
stable published digest and changes continuously. Acquisition accepts a per-ecosystem
`--expected-sha256` (`operator_pinned`) or, behind the explicit `--allow-unpinned` opt-in, records
the digest it observed (`observed_only`). The export is internally pinned by `inventory_sha256`
either way, so matching stays deterministic; what differs is whether the input was approved in
advance, and the receipt records which applied per archive.

Twenty-five new tests drive a fake reader and never open a socket: profile round-trip into
`load_profile` and `build_index`, read-only records, multi-ecosystem fetch, shared-advisory
deduplication, disagreeing archives, four unexpected-member shapes, four bound refusals, corrupt
archives, digest enforcement, the unpinned opt-in, five rejected source URLs, unsupported
ecosystems, pre-existing output directories and receipt contents. The changed files pass lint and
formatting against an unchanged repository-wide baseline, and the full suite passes: 1,191 tests. No
migration and no schema change.

**Real container and network qualification is outstanding.** No socket was opened and no image was
built or run while producing this slice; `scripts/validate_osv_acquisition.py` performs the real
fetch inside the pinned container and has not been executed. The image is not in any pinned image
inventory and is not promoted. Acquisition establishes no vulnerability position, performs no
matching and makes no model calls. Freshness is the moment of acquisition, and ecosystems that
were not requested are absent, not empty.

Next: run the container acceptance against the real export, then reachability, for which the
existing call index is the input and which remains unimplemented and unassumed.
