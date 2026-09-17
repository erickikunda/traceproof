# TraceProof CLI user and operator guide

**Scope:** laptop POC through Slice 46, SQLite schema 0009. Commands are run from the repository checkout on Linux/macOS using Python 3.12+. This guide describes implemented behavior. Git/GCS acquisition, HTTP API hosting, distributed workers, authenticated reviewers and OpenShift deployment are future work.

## Evidence gate version 3

The gate now recognizes conservative Flask request aliases, such as
`from flask import request as req`, in supported retained import-to-sink flows. Complete
file context and a non-rebound binding are required. Missing context or ambiguous/shadowed
aliases remain unsupported; passing means supported for review, not a verified vulnerability.

Old triage results remain unchanged. Gate version is part of request identity, so an old
key may conflict after this upgrade. Use `check-evidence BUNDLE_ID DECISION_JSON` for a
local recheck. Requesting new model advice requires a deliberately new key and consumes
the existing run budget/request allowance. It is not an automatic retry of old uncertain
calls. See [Slice 36](../development/slice-36.md) for exact limitations.

## Inspect retained storage

```bash
uv run traceproof storage-audit --max-entries 1000 --max-nodes 100000
```

Run while workers are idle. The command takes the worker lock and reports artifact IDs,
database-reference status and bounded logical file sizes for snapshots, extraction and
scan directories. It never deletes artifacts. Unreferenced or staging entries need review:
they may be useful for recovery. Do not interpret them as safe deletion candidates.

Check `status` and `issues`; limits or unreadable/linked entries make the result incomplete.
Counts exclude database/WAL/backups and are not allocated disk usage. There is no content
integrity check or search for missing directories. The audit may create the worker lock
file but does not modify stored results. See [Slice 35](../development/slice-35.md).

## Find a CodeQL extraction attempt

```bash
uv run traceproof extraction-history REPO_ID --limit 20
uv run traceproof extraction-history REPO_ID --run-id RUN_ID
uv run traceproof codeql-status EXTRACTION_ATTEMPT_ID
```

Use this history when extraction failed before a query attempt existed, or when you lost
the extraction ID. Query attempts remain in `scan-history`. Extraction history shows
recorded status, timing, version and resource settings; it neither starts work nor probes
process liveness. A stored successful result does not verify retained database files.

New records have creation timestamps. Legacy timestamps are null; dated attempts sort
first within each run, followed by undated IDs in descending order. Runs are grouped newest
first. Default limit is 100, maximum 1000; follow `next_offset` with `--offset`. Use exact
IDs for further actions. See [Slice 34](../development/slice-34.md).

## Find a previous import

```bash
uv run traceproof import-history --limit 20
uv run traceproof import-history --state paused --limit 20
uv run traceproof status IMPORT_ID
uv run traceproof import-control-status IMPORT_ID
uv run traceproof import-reports IMPORT_ID
```

History returns newest batches first with their IDs, latest dispatch state/revision and
intake counts. Optional filters are active, paused and cancelled. Follow `next_offset` using
`--offset`; default limit is 100, maximum 1000. Control changes or new imports can shift
later pages. Intake counts do not describe scan completion or findings. Cancelled batches
can retain unstarted rows, and active batches may already have completed intake.
See [Slice 33](../development/slice-33.md) for the projection contract.

## Cancel remaining import dispatch

```bash
uv run traceproof import-control-status IMPORT_ID
uv run traceproof import-control IMPORT_ID cancelled cancel-1 "No longer needed" --expected-revision 0
```

Use the revision returned by status. Cancellation is terminal for this import: it cannot
be resumed. Use pause when you intend to continue later. Already-started rows may finish;
completed work and report retrieval are preserved. `scan-import` reports cancelled with
no continuation offset when it observes the stop. `--rescan` cannot bypass it.

Explicit single-run operations and triage remain available; this cancels import dispatch,
not running processes. If replacement work is needed, explicitly submit a new import with
a new idempotency key. Repeating the original submission key returns the cancelled import.
Keep using this or a newer application version once cancellations exist. No migration beyond
0009 is needed. See [Slice 32](../development/slice-32.md).

## Pause and resume import dispatch

With writers quiesced, apply migration 0009 using `traceproof init`. Existing imports
remain active at revision 0. Then use the revision returned by status:

```bash
uv run traceproof import-control-status IMPORT_ID
uv run traceproof import-control IMPORT_ID paused pause-1 "Maintenance" --expected-revision 0
uv run traceproof import-control IMPORT_ID active resume-1 "Ready" --expected-revision 1
uv run traceproof worker IMPORT_ID
```

A pause takes effect at the next intake or batch-scan row boundary. Work already admitted
at a boundary may finish; no tool process is killed. `status IMPORT_ID` shows dispatch
state separately from row states. `scan-import` returns `dispatch_status: paused` and
`next_offset` for the next row. After resuming, invoke the worker or scan command again;
resume does not launch work. Existing snapshots/reports stay available.

Repeat an identical request key to recover from an uncertain response. A stale revision
or changed request with the same key is rejected; inspect current status before retrying.
History records reasons and revisions, with `--offset`/`--limit` pagination. This is a local
operator control, not authenticated approval. Explicit single-run commands and triage are
not blocked by import pause. See [Slice 31](../development/slice-31.md) for the full scope.

## Triage a candidate page

For synthetic local Ollama testing, with an approved model configuration:

```bash
uv run traceproof triage-budget RUN_ID 0 --max-requests 20
uv run traceproof triage-attempt REPO_ID ATTEMPT_ID examples/triage-ollama-config.json local-pass-1 --limit 5
uv run traceproof triage-report RUN_ID
uv run traceproof publish-report REPO_ID --run-id RUN_ID --attempt-id ATTEMPT_ID
```

The zero monetary budget above is for zero-priced local inference; priced models require
a suitable monetary cap and explicit source-transmission policy. Existing budgets remain
fixed. Replay policies require `--replay RESPONSE_JSON`; a shared replay fixture does not
measure candidate-specific detection quality.

Selection is from the exact attempt in fingerprint order. Default limit is 1, maximum 100.
Repeat the same key/configuration to reuse recorded calls. A new key can cause additional
calls and spend; batch keys do not deduplicate unrelated manual triage calls. Inspect JSON
`status` and the ledger after each page. Budget exhaustion, uncertain provider outcomes
and application errors halt processing. `next_offset` advances past recorded outcomes,
but stays on an application-error candidate. Do not treat a halted page as a successful
triage pass. `page_complete` describes only the selected page. Later publication is explicit.
See [Slice 30](../development/slice-30.md) for retry and stop semantics.

## Share a benchmark scorecard

```bash
uv run traceproof benchmark-history DATASET_ID
uv run traceproof benchmark-get DATASET_ID SCORECARD_ID --format html > scorecard.html
```

Open the exported HTML in a browser. It requires no server, JavaScript or external assets.
The top-level metric is a provisional candidate-location recall proxy, not confirmed recall.
Check evaluation completion and repository scope gaps before interpreting it. Precision
and confirmed recall remain unknown. Expand label/candidate details and provenance as
needed, and expand them before printing. Dataset identities may be sensitive; share with
the appropriate audience. JSON and CSV remain available for dashboards.

`benchmark-get` retrieves the exact saved publication without reevaluation. The same HTML
format works on `benchmark-evaluate`, which does evaluate its supplied inputs. See the
[Slice 29 contract](../development/slice-29.md).

## Supply a CodeQL query suite (.qls)

`scan-run` and `codeql-analyze` accept a trusted local `.qls` file in the same
positional argument as a single `.ql` query. Replace the example paths below with
existing, operator-approved suites compatible with the selected language and installed
CodeQL query packs. These are placeholders, not files shipped by TraceProof.

```bash
# Scan an already-ingested Python run with a suite.
uv run traceproof scan-run RUN_ID /absolute/approved-python-suite.qls --language python --query-timeout 600

# Scan an already-ingested Java run with a suite and a provisioned dependency profile.
uv run traceproof scan-run RUN_ID /absolute/approved-java-suite.qls --language java --java-profile source-only --java-dependency-profile /absolute/java-profile.json --query-timeout 600

# Alternatively, analyze an existing successful extraction with a compatible suite.
uv run traceproof codeql-analyze EXTRACTION_ID /absolute/approved-suite.qls --timeout 600
```

Use the same state directory/global CLI options as for the intake or extraction.
The Java dependency profile is optional when the repository does not require it;
choose the extraction profile and dependencies appropriate to the source.

Supply the suite from trusted operator tooling, not the repository being scanned.
TraceProof rejects query paths inside its scanned-artifact directory and passes the
suite to CodeQL for resolution. Provision all referenced query packs and dependencies
before an offline scan. For containers, bake them into the image or expose the suite
and referenced files through an approved read-only mount at the path passed to the CLI.
The fixed container acceptance scripts still select their own fixture-specific queries;
changing the application query argument does not expand that acceptance matrix.

A broader suite can produce additional static candidates and reports. It does not
expand TraceProof's qualified LLM evidence policies: unsupported rules remain available
as candidates but are not sent for model triage. Check `evidence-policy RULE_ID` for the
current rule policy. Coverage also depends on successful extraction and query completion.
The recorded query hash identifies the supplied entry file; it is not a complete
transitive hash of every query or pack referenced by a suite. Pin and retain those
operator-tooling dependencies separately for reproducibility.

## Tune CodeQL resources

```bash
uv run traceproof scan-run RUN_ID /absolute/approved.ql --threads 1 --ram-mb 4096
```

The same options work on `codeql-extract`, `codeql-analyze` and `scan-import`.
Defaults remain 2 threads and 2048 MB. Allowed ranges are 1–64 threads and 2048–262144 MB;
choose values your machine can support. Pipeline commands apply them to both stages.
CodeQL treats these as tuning inputs, not hard process limits. Leave room for the OS,
Python and JVM overhead; OpenShift pod requests/limits will require separate configuration.

`codeql-status` and `scan-report` expose each new attempt's `requested_resources`.
Older attempts have no inferred resource record. Changing options does not force an
existing batch row to run again: `scan-import` still requires `--rescan` for existing
query attempts. See [Slice 28](../development/slice-28.md) for scope and validation.

## Export original SARIF for a viewer

```bash
uv run traceproof scan-history REPO_ID
uv run traceproof get-sarif REPO_ID ATTEMPT_ID > results.sarif
```

Choose the exact query attempt, also available in a published report's `attempt_id`.
The command verifies repository scope, the stored SHA-256 and the 16 MiB file limit
before writing original bytes. Completed and partial attempts with a recorded digest
are eligible; unavailable, linked or modified artifacts fail. Nothing is rescanned.
Errors go to stderr with exit 1; check exit status because shell redirection can leave
an empty file on failure. Use a new destination to avoid overwriting an existing export.

Raw SARIF may expose source-related messages, flows, paths and diagnostics. Review it
before sharing; use the summary CSV for routine dashboard consumption. The original
SARIF does not include later TraceProof model/operator decisions. Consult the matching
report for readiness: partial or zero-alert output does not establish a secure repository.
See [Slice 27](../development/slice-27.md) for the retrieval contract.

## Export a snapshot file inventory (CycloneDX)

```bash
uv run traceproof get-sbom REPO_ID SNAPSHOT_ID > inventory.cdx.json
uv run traceproof get-sbom REPO_ID SNAPSHOT_ID --verify > inventory.cdx.json
```

The snapshot identifier appears in a published report's `snapshot_id`. Output is CycloneDX
1.6 JSON with one `file` component per recorded manifest entry, carrying that entry's
SHA-256 and size. The command verifies repository scope and refuses rather than emit a
partial document past the 20,000-component or 8 MiB bound.

**This is a file inventory, not a dependency bill of materials.** TraceProof does not parse
`package.json`, `pom.xml`, `go.mod`, `Cargo.toml`, `*.csproj` or any lockfile belonging to a
scanned repository, so the document contains no package identities, no Package URLs, no
resolved transitive dependencies and no license inventory. It carries no `vulnerabilities`
array: it establishes no vulnerability position, and an empty inventory of a given ecosystem
means no parser exists for it, never that the ecosystem is absent. Do not submit it where a
supply-chain attestation or a package SBOM is required.

Without `--verify` the document re-encodes the manifest recorded at intake. `--verify`
re-reads and re-hashes the stored snapshot first and records
`traceproof:manifest_verification: reverified`; it costs a full pass over the tree and fails
if the retained artifact has changed or been pruned. Output is deterministic — no publication
timestamp is included and the serial number derives from the snapshot identity — so an
unchanged snapshot always exports identical bytes.

File paths reveal repository structure; review before sharing. Errors go to stderr with
exit 1; check exit status because shell redirection can leave an empty file on failure.
See the [SBOM and OSV export roadmap](../plans/sbom-osv-export.md) for why package-level
SBOM and OSV output require new pipeline stages rather than a new encoder.

### Declared npm packages

```bash
uv run traceproof get-sbom REPO_ID SNAPSHOT_ID --packages > inventory.cdx.json
```

`--packages` additionally reads `package-lock.json`, `npm-shrinkwrap.json` and `package.json`
(and `pom.xml`, below) from the verified snapshot tree and adds one `library` component per declared package, with a
Package URL. Each file is re-hashed against its manifest record before being parsed; a
mismatch, an unreadable file, a non-JSON body or an oversized file is skipped and counted in
`traceproof:dependency_files_skipped` rather than silently dropped.

A lockfile yields `traceproof:resolution: pinned` with a concrete version. `package.json`
yields `declared_range`: the component carries **no** version, only a
`traceproof:version_constraint`, because a range is not a component identity. Both records can
appear for the same package and are kept distinct. `dev`, `optional` and `peer` declarations
are included and marked in `traceproof:declared_scopes` rather than dropped.

What this still does not establish: no transitive closure is resolved, because that needs a
build and a registry and TraceProof runs offline; `traceproof:transitive_dependencies` stays
`not_resolved`. A lockfile records what npm resolved when the lock was written, not what is
installed or deployed. npm `integrity` is recorded as a property, not as a CycloneDX hash,
because the tarball it describes was never fetched or verified. Manifests under
`node_modules/` are installed copies rather than declarations; they are counted in
`traceproof:excluded_declarations_ignored` and remain in the file inventory only. Ecosystems other
than npm, Maven and Go are not parsed at all, so an empty inventory never means a repository has no
dependencies — only that no parser exists for it yet.

### Declared Maven dependencies

`--packages` also reads `pom.xml`. Maven has **no lockfile**, so nothing it declares is ever
`pinned`: a stated version is `declared_version`, since nearest-wins mediation can still
override it at build time.

| `traceproof:version_source` | What the POM established |
|---|---|
| `literal` | the dependency's own `<version>` |
| `properties` | a `${...}` substituted from this file's `<properties>`, `<version>` or `<parent>` |
| `dependency_management` | a `<dependencyManagement>` entry in the same file |
| `inherited_or_managed_elsewhere` | nothing — the component carries no version |

Version ranges (`[1.7,2.0)`) become `declared_range` and carry a constraint, not a version.

Parent POMs are **never followed**, even when the parent sits in the same snapshot, so
`traceproof:inheritance_resolved` is always `false`. A version inherited from a parent, defined
by a property declared elsewhere, or managed by an imported BOM stays `unresolved_version` — the
component appears with no version rather than a guessed one. Imported BOMs, poms carrying a
`<parent>`, and profile dependencies are counted in `traceproof:ecosystem_notes`. Profile
dependencies are conditional on activation and are never emitted as components. Poms under
`target/` are build output and counted as ignored.

Any `<!DOCTYPE` or `<!ENTITY` declaration causes the file to be refused before parsing and
counted as `maven:doctype_refused`. A real `pom.xml` needs no DTD, and Python's XML parser
expands internal entities, so refusing is the conservative reading rather than a limitation.

### Declared Go modules

`--packages` also reads `go.mod`. `go.sum` is **not** read: it covers the whole module graph
rather than what a build resolves, so treating it as an inventory would over-report.

The directive that matters most is `replace`, because it changes what is actually built:

| go.mod | Reported |
|---|---|
| `require github.com/a/b v1.0.0` | `declared_version`, `v1.0.0` |
| `replace github.com/a/b => github.com/c/d v2.0.0` | `a/b` becomes `replaced` with **no version**; `c/d@v2.0.0` is emitted |
| `replace github.com/a/b => ./local` | `a/b` becomes `replaced`; no registry component |
| `replace github.com/a/b v1.0.0 => ...` | applies only when `v1.0.0` is the required version |
| `exclude github.com/a/b v0.1.0` | counted in `traceproof:ecosystem_notes`, never emitted |

A `replaced` component carries no version and is therefore **never matched against advisories**.
That is deliberate: if the replacement is a patched fork, matching the original's version would
report a vulnerability the build does not have.

`// indirect` requirements are marked `indirect` in `traceproof:declared_scopes` rather than
dropped, so Go shows transitive modules that npm manifests and Maven POMs do not. This is not
closure resolution — the Go tool recorded those entries and TraceProof only read them, so
`traceproof:inheritance_resolved` stays `false`.

Go versions carry a `v` prefix while OSV Go records use plain semantic versions; ordering strips
the prefix and exact version lists are tried both ways, so `v1.9.1` matches a record written as
`1.9.1`. `go.mod` files under `vendor/` and `testdata/` are counted as ignored.

Go import evidence under `--usage` is **exact**, unlike Maven's: an import path is the module path
or a package below it, guaranteed by the Go toolchain, so `github.com/gin-gonic/gin/binding`
matches module `github.com/gin-gonic/gin` and `github.com/a/bc` does not match `github.com/a/b`.
A Go `not_observed` is therefore stronger evidence than a Maven one — but still not evidence of
non-use, since build tags, generated code and indirect dependencies leave no import.

## Acquire the OSV export (networked, separate container)

Acquisition is the **only** networked OSV step and runs in its own container; matching never opens
a socket.

```bash
uv build
docker build -f containers/Containerfile.osv-acquisition -t traceproof:osv-acquisition-linux-poc .
uv run python scripts/validate_osv_acquisition.py \
  --image traceproof:osv-acquisition-linux-poc work/osv-qualification
```

Add `--platform linux/amd64` to `docker build` for an x86_64 cluster; the pinned base digest is a
multi-arch index and resolves per architecture. Both builds are recorded in
`containers/osv-acquisition-image.json`, and comparing two full exports found zero
architecture-attributable differences — but the amd64 image has only been exercised under
emulation, never on native hardware.

Two exports taken at different times will **not** share an `inventory_sha256`, because the
upstream export changes continuously: a ten-hour gap between qualification runs added one
advisory and revised another, out of 245,373. Comparing digests across machines compares
acquisition times, not architectures. Use `--expected-sha256` where a reproducible input is
required.

The validator drives the image from the host with the same hardened runtime the Git acquisition
uses (read-only root, dropped capabilities, no new privileges, bounded CPU/memory/PIDs). It
checks that an unallowed host is refused without creating an output directory, that unpinned
acquisition requires the opt-in, that a wrong pinned digest is refused, and that the acquired
export then loads with `--network none`. Add `--ecosystem` to select what to fetch; the default
is Go and Maven. To acquire directly rather than qualify:

```bash
docker run --rm --network bridge --read-only --cap-drop ALL \
  --tmpfs /work:rw,size=2g --tmpfs /tmp:rw,size=2g \
  --mount type=bind,source="$PWD/work/export",target=/export \
  traceproof:osv-acquisition-linux-poc \
  https://osv-vulnerabilities.storage.googleapis.com /export/osv \
  --ecosystem Go --ecosystem Maven \
  --allowed-host osv-vulnerabilities.storage.googleapis.com --allow-unpinned
```

### Size the export to what you scan

Measured against the live export during qualification:

| Ecosystems | Archive download | Records | Expanded | Offline load + index | Peak RSS |
|---|---|---|---|---|---|
| Go + Maven | 21 MiB | 16,363 | 51 MiB | ~3 s | ~120 MiB |
| Go + Maven + npm | 226 MiB | 245,373 | 431 MiB | ~50 s | ~1.7 GiB |

npm alone carries 229,010 of those records. Without a cache that cost is paid on **every**
`get-osv` or `get-sbom --database`, because the profile is re-hashed and the index rebuilt each
run. Fetch only the ecosystems you actually scan; a Java-only estate has no reason to carry npm.
Allow at least 4 GiB to a container matching against a full three-ecosystem export.

### Caching the index, and what it gives up

```bash
uv run traceproof get-osv REPO_ID SNAPSHOT_ID /absolute/osv-profile.json --cache
uv run traceproof get-osv REPO_ID SNAPSHOT_ID /absolute/osv-profile.json --cache --refresh-cache
```

`--cache` writes a derived index under `<state-dir>/osv-cache/`, keyed by the profile's own
digest, and reuses it on later runs. Measured against the three-ecosystem export: **52.8 s
without a cache, 10.5 s on a cache hit**, with a 56 MiB cache file. The first `--cache` run is
slower than none at all (71.9 s) because it both verifies and writes.

**The saving is the verification.** The uncached path re-hashes all 245,373 record files to prove
the database still matches the `inventory_sha256` its profile pins; a cache hit skips that
entirely and serves the contents recorded when the cache was written. A record modified after the
cache was built is therefore **not detected** — the uncached path refuses that database outright,
while a cache hit serves the previously approved contents. That is why caching is opt-in.

Every document records which path ran, in `traceproof:osv_database_verification`:

| Value | Meaning |
|---|---|
| `reverified` | every record was re-hashed against the pinned inventory this run |
| `cached` | a derived index was reused; records were not re-read |

A cache is accepted only when it names the same `inventory_sha256` and record count the profile
pins, so pointing at a different or updated export rebuilds automatically. A corrupt, truncated,
symlinked or schema-mismatched cache is ignored and a verified rebuild runs instead; a cache that
cannot be written never fails the scan. Use `--refresh-cache` to force full verification and
rewrite. Treat the cache directory as local state with the same trust as the database itself, and
prefer `--refresh-cache` or no cache at all when that trust is what you are testing.

The output directory must not already exist — leftover records would otherwise enter the pinned
inventory. On success it holds `osv-profile.json` (what `get-osv` and `get-sbom --database`
consume), `osv-acquisition-receipt.json`, and read-only `records/`. Hand the directory to the
offline scanner the same way acquired repositories are handed over.

The source must be credential-free HTTPS on an explicitly allowed host, and redirects are refused
outright because a redirect could leave the validated host. An unexpected archive member — nested
paths, non-JSON files, hidden names — **aborts the acquisition** rather than being skipped, since
a silently incomplete database would later be reported as fully evaluated.

### Pinned versus observed freshness

Git acquisition pins a commit and GCS pins a generation. The OSV export has no stable published
digest and changes continuously, so it cannot be pinned the same way:

| Mode | How | Recorded as |
|---|---|---|
| Approved in advance | `--expected-sha256 npm=<sha256>` per ecosystem | `operator_pinned` |
| Observed at fetch time | `--allow-unpinned` | `observed_only` |

`--allow-unpinned` is required rather than implied, so an unapproved fetch is a deliberate choice.
Either way the resulting export is internally pinned by `inventory_sha256`, so matching is
deterministic; what differs is whether the input was approved beforehand. The receipt records
which applied per archive, and its limitations state that freshness is the moment of acquisition
and that unrequested ecosystems are **absent, not empty**.

Acquisition establishes no vulnerability position and performs no matching. It makes no model
calls.

## Match declared packages against a pinned OSV export

```bash
uv run traceproof get-osv REPO_ID SNAPSHOT_ID /absolute/osv-profile.json > osv-results.json
uv run traceproof get-sbom REPO_ID SNAPSHOT_ID --packages --database /absolute/osv-profile.json
```

`get-osv` emits an OSV-Scanner-**shaped** `results.json` grouped by the file that declared each
package; it is not an OSV-Scanner run, and a `traceproof` block carries the coverage that a
scanner result has no field for. `get-sbom --database` instead adds a CycloneDX `vulnerabilities`
array to the inventory. Both refuse unless `--packages` supplied the components.

The database is **operator-supplied and pinned**; TraceProof fetches nothing and updates nothing.
The profile names a records directory and one `inventory_sha256` over its canonical inventory:

```json
{
  "version": "1",
  "source": "https://osv-vulnerabilities.storage.googleapis.com/",
  "exported_at": "2026-09-01T00:00:00Z",
  "ecosystems": ["npm", "Maven"],
  "records_directory": "records",
  "record_count": 2,
  "inventory_sha256": "<sha256 of the canonical {path: sha256} map>"
}
```

A changed, added or removed record fails the check and no results are produced. Withdrawn
advisories are loaded, counted and never matched.

### What a match means, and what it does not

A match is a **candidate**. It says a declared version fell inside an advisory's affected range,
and nothing more: no reachability, no call path, no evidence the vulnerable code is used or the
component is deployed. In CycloneDX the analysis state is always `in_triage` — never
`exploitable`, never `not_affected`.

Three bases produce a match: exact membership of an advisory's `versions` list, a `SEMVER` range
under semantic-version precedence, and an `ECOSYSTEM` range on a Maven package under Maven's
`ComparableVersion` ordering. An ordering is bound to a range type and an ecosystem — it is never
inferred from how a version string happens to look, so a `SEMVER`-typed range is still refused
over a version like `5.3.9.RELEASE`. Anything without an implemented ordering is a recorded gap,
not a verdict:

| Gap | Why |
|---|---|
| `range_type_ECOSYSTEM_<ecosystem>` | no ordering is implemented for that ecosystem |
| `range_type_GIT_<ecosystem>` | commit ranges are not evaluated |
| `version_not_semver` | a `SEMVER` range met a version with no semantic-version ordering |
| `semver_range_bound_unordered` | the advisory's own bounds do not parse |
| `component_state_no_version` | the component never had a resolved version |
| `component_state_ecosystem_not_in_database` | the export carries no advisories for that ecosystem |
| `component_state_database_incomplete` | the export held records the loader could not read |

Maven ordering is a faithful port of `ComparableVersion`, validated against the ordering and
equivalence vectors in Maven's own test suite: `5.3.9` sorts below `5.3.10`, `1.0-SNAPSHOT` below
`1.0`, and `3.1.0.RELEASE` equals `3.1.0`. Maven also still matches on exact version lists, which
GHSA-derived records generally carry.

`traceproof:osv_component_states` is the field to read before concluding anything:

- `evaluated_no_match` — the database was fully consulted for this component, and it covered that
  ecosystem and held no unreadable records

Read `traceproof:osv_records_unread` alongside these. If it is not `0`, the export held records
the loader could not parse, `traceproof:osv_components_fully_evaluated` is `0`, and **no**
component was evaluated against a complete database — including the ones reporting matches.
- `partially_evaluated` — something about it could not be evaluated
- `not_evaluated` — no resolved version, or an ecosystem the export does not cover
- `matched` — at least one candidate

**Only `evaluated_no_match` supports any negative statement.** A Maven repository whose versions
come from parent POMs will still be largely `not_evaluated` — ordering fixes range evaluation, not
missing versions — and an empty result there says close to nothing. An empty result never means a
repository is free of known vulnerabilities.

## Import evidence for declared packages

```bash
uv run traceproof get-sbom REPO_ID SNAPSHOT_ID --packages --usage
uv run traceproof get-osv REPO_ID SNAPSHOT_ID /absolute/osv-profile.json --usage
```

`--usage` scans first-party source for imports of each declared package and records a state per
component. **This is import evidence, not reachability analysis.**

| State | Meaning |
|---|---|
| `import_observed` | first-party source names this package in an import or require |
| `not_observed` | no import was found — **not** evidence that the package is unused |
| `not_evaluated` | no source of that language was read |

The asymmetry is the point. `import_observed` raises priority. `not_observed` clears nothing:
transitive use, dynamic `require`, reflection, framework wiring, service loaders and
configuration-driven instantiation all leave no import in first-party source. Check
`traceproof:usage_files_skipped` before reading anything into a `not_observed` — a skipped file
may hold the very import that would have changed it.

A vulnerability's CycloneDX `analysis.state` stays `in_triage` whatever the usage state. Usage
prioritizes work; it never adjudicates a candidate.

### What the scan does and does not read

Detection is **lexical, not parsed** (`traceproof:usage_detection_method`), so a specifier inside
a comment or string can be reported. That is the conservative direction: over-reporting says
investigate, under-reporting would say clear. `node_modules/`, `target/`, `build/`, `dist/`,
`out/` and `vendor/` are excluded as not first-party, and `*.min.js`/`*.bundle.js` are excluded
because a bundle inlines its dependencies and would report every one of them as imported.

For Maven, an import is matched against the dependency's groupId prefix. That correspondence is a
**convention, not a rule** — `junit:junit` publishes `org.junit`, so a project using JUnit reports
`not_observed`. Treat Maven `not_observed` as carrying almost no information.

No call graph is resolved (`traceproof:usage_call_graph_resolved: false`) and no vulnerable symbol
is matched (`traceproof:usage_vulnerable_symbol_matching: none`). OSV records for npm and Maven
carry version ranges, not affected functions, and third-party code is not in the snapshot at all,
so there is nothing for a call path to reach.

### Go symbol evidence

When a Go match comes from an advisory that carries `ecosystem_specific.imports` — which the Go
vulnerability database publishes and no other parsed ecosystem does — `--usage` adds a second,
finer state per vulnerability:

| `traceproof:go_symbol_evidence` | Meaning |
|---|---|
| `symbol_referenced` | source imports the vulnerable package and names one of the advisory's symbols |
| `package_imported` | the vulnerable package is imported; no named symbol was referenced |
| `package_not_imported` | the module is used, but that package path is not imported |
| `no_symbol_data` | the advisory carries no import data |
| `not_evaluated` | no Go source was read |

`symbol_referenced` also lists what was found in `traceproof:go_symbols_referenced`.

`package_not_imported` is the strongest negative this tool produces and is **still not a safety
conclusion**. An imported package can call the vulnerable one internally, a transitive dependency
can import it, and generated or build-tagged code may be absent from the snapshot. The CycloneDX
analysis state stays `in_triage` for every state above.

The scan is lexical. It resolves the identifier an import binds — exactly when aliased,
conventionally otherwise, since a package's declared name need not match its path — then searches
for `identifier.Symbol`. A method symbol like `Decoder.Decode` is searched by its receiver type,
because a call site cannot be resolved lexically, so `package_imported` versus `symbol_referenced`
is a priority signal rather than a proof of use. Blank imports (`_`) bind no name. Dot imports
(`.`) put symbols in scope unqualified and are counted in
`traceproof:go_dot_imports_unresolvable` rather than guessed at. Platform constraints
(`goos`/`goarch`) are recorded but never applied, since the build target is unknown —
`traceproof:go_platform_filtering` is always `none`.

No call graph is resolved. `govulncheck` answers the reachability question by building the whole
program including dependencies; TraceProof has neither the dependencies nor the build, so it
reports references rather than reachability.

## Retrieve reports for an import batch

After `scan-import`, inspect report availability or export a dashboard input:

```bash
uv run traceproof import-reports IMPORT_ID --limit 100
uv run traceproof import-reports IMPORT_ID --offset 100 --limit 100
uv run traceproof import-reports IMPORT_ID --limit 1000 --format csv > import-reports.csv
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format html > report.html
```

Rows stay tied to the runs admitted in that import. Status distinguishes intake not ready,
not analyzed, report not published and published. A published report can describe failed
analysis; check analysis status and static readiness. Candidate counts are observations,
not verified vulnerabilities. Blank CSV counts mean unknown, not zero.

Only the newest report version matching the admitted run's latest attempt is selected.
There is no fallback to older reports or newer repository submissions. Publication captures
advisory/review state at that time; republish to include later reviews. JSON includes
page counts and `next_offset`; CSV contains only selected rows with stable ID columns.
Default page size is 100, maximum 1000. Separate pages may observe new work. This read-only
command makes no model calls and includes no source snippets. See the
[Slice 26 contract](../development/slice-26.md).

## Start here

TraceProof captures source, indexes Python, runs an approved local CodeQL query, and publishes reviewable candidates. Models can advise on those candidates; they cannot confirm vulnerabilities or suppress them. Operator assertions are recorded separately. A successful command, zero candidates, or `ready_for_review` does not establish that a repository is secure.

Install the locked development environment and initialize local storage:

```bash
uv sync --locked
uv run traceproof --help
uv run traceproof init
uv run traceproof get-report --help
```

Use `uv run traceproof` in the examples below. An activated project virtual environment also provides `traceproof`. Commands accept `--help`; the global `--state-dir` option goes **before** the command. Its default is `.traceproof` relative to the current directory. Keep using the same state directory throughout a workflow:

```bash
uv run traceproof --state-dir /absolute/local/state init
```

`init` creates or upgrades the database; it is not a reset command. Current migrations are applied explicitly, not on every read. Keep state on trusted local disk, not shared network storage. Source archives, raw tool outputs and evidence can be sensitive. The local OS account is the access boundary; repository ownership checks are not multi-user authentication.

## Understand the identifiers and outputs

Copy IDs from actual command responses; uppercase names below are placeholders.

| Identifier | Meaning / where to obtain it |
| --- | --- |
| `REPO_ID` | Your stable repository label in the CSV |
| `IMPORT_ID` | One CSV admission, returned by `import-csv` |
| `RUN_ID` | One admitted row's run, returned in import results |
| `SNAPSHOT_ID` | Captured source identity, returned by `run-status` after worker success |
| `EXTRACTION_ID` | CodeQL database extraction attempt, returned by `codeql-extract` |
| `ATTEMPT_ID` | Security query attempt, returned by `codeql-analyze` / `scan-report` |
| `CANDIDATE_FINGERPRINT` | Candidate identity within a scan, returned by `scan-report` |
| `BUNDLE_ID` | Bounded evidence package, returned by `build-bundle` |
| `REPORT_ID` | Immutable published summary version, returned by `publish-report` |

Commands normally print JSON. Request/storage errors produce a nonzero exit code, often with JSON on stderr. Durable failures can still exit zero: inspect row states, extraction/query `status`, bundle gaps, triage disposition and readiness. Scripts must inspect both the exit code and returned fields. `acceptance-run` and benchmark validation have additional explicit failure exit behavior.

To recover run or query-attempt IDs, including work without a published report:

```bash
uv run traceproof run-history REPO_ID --limit 100
uv run traceproof scan-history REPO_ID --limit 100
uv run traceproof scan-history REPO_ID --run-id RUN_ID --offset 0 --limit 100
```

Follow `next_offset` until null. Pages contain at most 1000 rows, sorted by newest run admission and then newest attempt within each run. New work can shift offset pages between requests; this is not a frozen export. Failed attempts remain visible, unknown counts are null, and a run with no query attempt has no scan-history rows. Extraction attempts are separate: use `extraction-history` to find IDs for `codeql-status`. Use `report-history` for published summary IDs.

## First walkthrough: capture and index synthetic source

The included generator creates a small benign archive. It does not execute the source.

```bash
uv run python examples/create_archive.py --output work/guide-input
uv run traceproof import-csv work/guide-input/repos.csv --input-root "$PWD/work/guide-input" --key guide-import-1
uv run traceproof worker IMPORT_ID --max-items 1
uv run traceproof import-status IMPORT_ID
uv run traceproof run-status RUN_ID
uv run traceproof verify-snapshot SNAPSHOT_ID
uv run traceproof index-run RUN_ID
uv run traceproof query-index RUN_ID --kind symbols
uv run traceproof repo-report synthetic-demo --run-id RUN_ID --format markdown
```

Expected checkpoints: the row is admitted, worker captures a snapshot, the run becomes `snapshotted`, and the Python index becomes ready. `repo-report` is **index coverage**, not the published vulnerability summary. Re-running indexing resumes checkpoints or reuses the same completed snapshot/parser index after source verification.

For your own inputs, CSV requires `repo_id,source_type,source_uri,owner,classification`; optional columns are `sha256,scan_profile`. Use `source_type=pvc`, an absolute archive path beneath `--input-root`, and `scan_profile=standard` if supplied. This source type works on laptop disk; no PVC is required locally. Supported archives are TAR, TAR.GZ and ZIP. Git URLs and GCS objects are not yet acquired.

Finish writing archives before admission. Supply `sha256` to pin original archive bytes before capture. Without it, capture time determines the pinned bytes. Reusing an import key with identical CSV bytes and root retrieves the same admission; changed source should use a new submission key. Invalid rows are reported independently. Links, path traversal and ambiguous archive members are rejected; nested archives are not recursively unpacked.

## Run CodeQL and inspect candidates

Before scanning, run `uv run traceproof doctor --query /absolute/approved.ql` for local
prerequisite diagnostics and suggested fixes. `blocked` exits 1; omitting the query can
return `incomplete` with exit 0. This command neither runs CodeQL nor changes the schema.
It checks availability, not query compilation, sufficient capacity or enterprise approval.
See [preflight details](../development/slice-22.md).

For an already captured run, the source-only stages can be executed together:

```bash
uv run traceproof scan-run RUN_ID /absolute/approved.ql --extraction-timeout 300 --query-timeout 600
```

This indexes, checks readiness, extracts, queries and publishes the exact attempt. It
never invokes an LLM. Inspect returned `status` and IDs: index/extraction failures stop
with no new report, while failed query attempts produce incomplete reports. Repeating
the command starts fresh extraction/queries; it is not an automatic retry. If publication
fails, find the attempt with `scan-history` and publish it explicitly. Individual stages
below remain useful for diagnosis. See [scan-run details](../development/slice-21.md).

To scan a captured CSV batch sequentially, use `scan-import IMPORT_ID QUERY --limit 5`.
Follow its `next_offset` with `--offset`; page positions include rejected/uncaptured rows.
The default limit is one row. Existing query attempts, including failures, are skipped
unless you pass `--rescan`. Inspect each row's outcome; mixed outcomes can exit zero.
Expected row errors do not block later rows, but infrastructure errors stop the command.
Per-run results are durable; save the JSON batch summary yourself. See
[batch scanning](../development/slice-25.md).

CodeQL must be on PATH, with an approved query and its dependencies installed locally. TraceProof does not download packs during analysis. Local acceptance has used CodeQL 2.27.0 and `codeql/python-queries` 1.8.10; the enterprise must supply its approved versions and usage entitlement.

```bash
uv run traceproof codeql-extract RUN_ID --timeout 300
uv run traceproof codeql-status EXTRACTION_ID
uv run traceproof codeql-analyze EXTRACTION_ID /absolute/CodeInjection.ql --timeout 600
uv run traceproof scan-report REPO_ID --run-id RUN_ID
```

Extraction uses Python build mode `none`. Inspect extraction success before analysis. Query failure, timeout and invalid SARIF are durable outcomes. The benign first walkthrough may have no candidates. For a reproducible vulnerable/fixed/incomplete demonstration, use a **new** output directory and an installed `CodeInjection.ql` entry:

```bash
uv run traceproof acceptance-run work/guide-acceptance /absolute/CodeInjection.ql --timeout 300
```

This creates isolated state under `work/guide-acceptance/state`, synthetic input archives, reports in five formats and `acceptance.json`. It checks that the seeded case has a candidate, its fixed counterpart does not, and an invalid Python fixture remains incomplete. It makes no model calls. The runner gates analysis on indexing; individual CLI stages remain separately callable, so operators must inspect gates themselves.

To inspect this state, add `--state-dir work/guide-acceptance/state` before every subsequent command. Repository IDs are `acceptance-vulnerable`, `acceptance-fixed` and `acceptance-incomplete`; run/report IDs are in the scorecard.

## Inspect evidence and request advisory triage

For a candidate returned by a scan:

```bash
uv run traceproof build-bundle ATTEMPT_ID CANDIDATE_FINGERPRINT
uv run traceproof bundle-status BUNDLE_ID
uv run traceproof evidence-policy py/code-injection
uv run traceproof triage-budget RUN_ID 100000
uv run traceproof triage BUNDLE_ID examples/triage-replay-config.json guide-triage-1 --replay examples/triage-replay-response.json
uv run traceproof triage-report RUN_ID
```

The supplied replay is offline, uses fictional rates/usage and abstains. `100000` micro-USD equals $0.10 in the ledger, not a replay charge. The run budget cannot be changed once set. Partial bundles, unsupported rules and exhausted budgets prevent provider invocation. Reusing the same triage key with identical inputs retrieves the recorded result; a different request needs a different key and may consume budget.

Each new budget also has a fixed request limit, default 100. Configure it at creation
with `triage-budget RUN_ID 0 --max-requests 20` for a zero-priced local run, for example.
All distinct recorded requests count, including skipped or failed ones. A repeated key
does not consume another slot. The ledger exposes `max_requests` and `remaining_requests`;
exhaustion blocks new keys without invoking a provider. Migration 0008 gives existing
budgets a 100-request limit and preserves their history. See
[request-limit details](../development/slice-24.md).

Evidence bundles have fixed source/envelope limits. Missing context stays explicit. Model proposals are `needs_review`, `likely_false_positive` or `abstain`. The evidence gate supports narrow code-injection and command-injection claims; acceptance is not independent proof of exploitation. No model proposal removes a raw candidate.

For targeted inspection, `source-evidence RUN_ID PATH LINE END_LINE` reads a verified snapshot range; `call-context RUN_ID PATH --module-root ROOT` provides conservative call candidates. `expand-bundle BUNDLE_ID REQUEST_JSON` accepts a JSON array of objects containing `path`, `line`, `end_line`, `reason`, creating an immutable child within existing caps. Expansion is bounded to four requested ranges per step and two steps. Inspect its result before separately triaging the child with a new key. `check-evidence BUNDLE_ID DECISION_JSON` validates claims locally without a model call.

### Live providers

For local POC inference, run an Ollama daemon with a locally installed completion model,
edit `examples/triage-ollama-config.json` to select it, then use:

```bash
uv run traceproof triage-budget RUN_ID 100000
uv run traceproof triage BUNDLE_ID examples/triage-ollama-config.json local-triage-1
```

No API key or `--replay` is needed. The endpoint is numeric loopback only, source/classification
opt-in remains mandatory, and zero configured rates represent local compute without an
estimated monetary cost. Ensure your daemon/model is local-only. A successful model reply
must still pass evidence checks and never automatically confirms a vulnerability.
See [Ollama setup and limits](../development/slice-23.md).

Only `triage` with a non-replay configuration invokes a provider. Cloud operation requires an explicitly allowed source classification, HTTPS endpoint/host, model ID, pricing and transmission opt-in. Keep cloud credentials in the designated environment variable, outside source archives and configuration files. OpenAI uses Responses; Anthropic uses Messages. Ollama uses the local policy above. No automatic provider fallback is available.

Configuration fields:

| Field | Operator responsibility |
| --- | --- |
| `provider`, `model` | `openai` or `anthropic`, plus the approved model identifier |
| `endpoint`, `allowed_endpoint_hosts` | Full approved HTTPS endpoint and exact hostname allowlist |
| `allowed_classifications` | Source classifications approved for this endpoint |
| `allow_source_transmission` | Must explicitly be `true` to send source |
| `api_key_env` | Name of environment variable containing the key; explicitly use `TRACEPROOF_ANTHROPIC_API_KEY` for Anthropic to avoid the OpenAI default |
| `ca_file` | Optional local CA file for TLS verification |
| `input_micro_usd_per_1k`, `output_micro_usd_per_1k` | Operator-supplied rates, in micro-USD per thousand tokens; no built-in prices |
| `max_output_tokens`, `timeout_seconds` | Output and request bounds; defaults 1024 tokens and 60 seconds |

Invoke `triage BUNDLE_ID CONFIG_JSON KEY` without `--replay`. The transport disables inherited proxies, redirects and retries. A bank gateway requiring proxy routing or another authentication method needs integration work; do not assume this local adapter covers it. Actual gateway/model compatibility and retention settings have not been validated by offline tests.

Unknown usage, interrupted requests and ambiguous provider failures retain reservations. A later triage operation marks interrupted running calls unknown; a read alone does not reconcile them. Do not clear ledger entries or automatically issue a new key to retry a possibly charged call. There is no operator refund/reconciliation command yet. Anthropic cache tokens are unexpected because caching is not requested; reported cache usage keeps accounting unknown. Configured reservations are not provider invoices or a guaranteed external spending limit.

## Publish, select and share a report

```bash
uv run traceproof publish-report REPO_ID
uv run traceproof report-history REPO_ID
uv run traceproof resolve-report REPO_ID --selection latest-attempt
uv run traceproof resolve-report REPO_ID --selection latest-completed
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format html > report.html
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format markdown > report.md
uv run traceproof get-report REPO_ID --report-id REPORT_ID > report.json
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format scan-csv > scan.csv
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format candidates-csv > candidates.csv
```

Publication reads stored state without invoking analysis. New triage/review state needs a new publication to appear in summaries; identical inputs reuse the same report. Exact report IDs stay immutable. Use `publish-report --run-id RUN_ID --attempt-id ATTEMPT_ID` for historical work.

`latest-attempt` never falls back to older work. `latest-completed` selects published Python static review-ready work, and its JSON envelope discloses the current run/attempt plus a warning if the chosen report is older. It does not claim security completion. No eligible report returns a null report with a warning. Preserve the envelope when sharing a historical selection; exporting only its embedded report loses the current-work disclosure. Selection is currently limited to 10,000 report versions per repository.

| Command | Question answered |
| --- | --- |
| `run-status` | Was source captured? |
| `run-history` / `scan-history` | Which runs and query attempts exist, including unpublished work? |
| `repo-report` | What Python syntax was indexed, and where are the gaps? |
| `scan-report` | What did this static-analysis attempt observe? |
| `triage-report` | What advice and costs were recorded for the run? |
| `resolve-report` | Which published report fits my selection, and is it current? |
| `get-report --report-id` | What did this exact immutable summary say? |

For dashboards, join scan and candidate CSVs on `report_id`. Scan CSV has report-level counts; candidate CSV has candidate rows. Preserve scan rows when there are zero candidates. Unknown counts remain unknown, not zero. Summary formats omit raw source, model prose and review notes, but metadata and paths can remain sensitive. Raw scan/evidence/history commands expose more detail.

`compare-reports REPO_ID BASELINE_REPORT_ID CURRENT_REPORT_ID --format markdown` compares exact versions without scanning. One-sided observations are not automatically fixed/new vulnerabilities; scope changes and ambiguous matches stay explicit.

## Record an operator review

First inspect `review-history REPO_ID ATTEMPT_ID CANDIDATE_FINGERPRINT` and the evidence bundle. Save a request such as the following, replacing the bundle placeholder and using the current history revision (zero initially):

```json
{
  "reviewer_label": "local-operator",
  "state": "needs_review",
  "rationale": "Confirm the input trust boundary with the application owner.",
  "bundle_id": "REPLACE_WITH_ACTUAL_BUNDLE_ID",
  "evidence_ids": [],
  "expected_revision": 0
}
```

```bash
uv run traceproof record-review REPO_ID ATTEMPT_ID CANDIDATE_FINGERPRINT review.json guide-review-1
uv run traceproof publish-report REPO_ID
```

Allowed states are `confirmed`, `false_positive`, `needs_review`, `deferred`. Definitive assertions require a ready bundle and valid evidence citations. Review keys are idempotent; a stale revision requires reading history before intentionally making another assertion. History is append-only, reviewer identity is self-declared, and these assertions do not set independent verification or measured precision.

## Benchmark evaluation

Keep labels outside analyzed archives. `benchmark-schema` prints manifest, labels and evaluation-plan schemas. `benchmark-check MANIFEST --labels LABELS` checks the contract; add `--check-local-snapshots` for stored identity alignment. Example files in `examples/` have synthetic placeholder digests and are not a real corpus.

`benchmark-evaluate MANIFEST LABELS PLAN --format markdown` evaluates exact published report IDs against evaluator-only labels without running scans. The plan pins analysis configuration and report selection. Results are provisional candidate-location recall proxies, not confirmed recall or precision. The 50-repository bank benchmark has not been run. See [evaluation details](../development/slice-11.md).

For dashboard ingestion, use `--format summary-csv`, `repositories-csv`, `labels-csv` or
`candidates-csv` and redirect each output to a separate file. Keep canonical JSON too.
Each populated CSV row carries the scorecard ID and input digests; verify they match
before joining on scorecard/repository IDs. Never sum the one-row summary after joining
detail tables. Null metrics are blank, zero remains zero, and lists/count maps are JSON
cells. Empty detail tables have headers only, so retain the summary. These exports expose
evaluator labels and matching metadata; share only with the authorized evaluation audience.
See [benchmark CSV contracts](../development/slice-17.md).

Evaluator version 2 also reports results by CWE in JSON and Markdown. Use
`--format weaknesses-csv` to export those rows. Class denominators retain missing,
ambiguous and unsupported labels. `no_labels` means no measurable recall value;
`incomplete` means unresolved evaluation gaps; `evaluated` may still include misses.
Do not average class percentages: sum numerators and denominators for the overall proxy.
Join using scorecard ID and CWE. Reevaluation creates new scorecard IDs; legacy results
are unchanged. See [per-class metrics](../development/slice-18.md).

To save an evaluation for later retrieval, run `init` for migration 0007, then:

```bash
uv run traceproof benchmark-publish MANIFEST LABELS PLAN
uv run traceproof benchmark-history DATASET_ID --limit 100
uv run traceproof benchmark-get DATASET_ID SCORECARD_ID --format markdown
uv run traceproof benchmark-get DATASET_ID SCORECARD_ID --format weaknesses-csv
```

Publication reuses identical scorecards and stores changed evaluations as separate IDs.
Retrieval supports JSON, Markdown and all five benchmark CSV formats without reevaluation
or input files. History includes incomplete publications. Protect evaluator-sensitive
records and retain approved inputs separately for reproducibility. See
[durable scorecards](../development/slice-19.md).

Use `benchmark-compare DATASET_ID BASELINE_SCORECARD_ID CURRENT_SCORECARD_ID --format
markdown` to compare saved evaluations. Incompatible datasets, labels, evaluators, rule
sets or incomplete results produce explicit reasons and unknown deltas. Comparable
results show provisional location matches gained/lost and current-minus-baseline proxy
deltas. Query/tool changes are disclosed, not assigned causal credit. No scans or input
files are needed. See [benchmark comparison](../development/slice-20.md).

## Recovery and routine operations

| Symptom | Action |
| --- | --- |
| Database uninitialized / older schema | Verify `--state-dir`, quiesce writers and run `init`; preserve a consistent backup before upgrades |
| Another local worker holds the lock | Let it finish; do not remove the lock to force concurrent work. Process death releases the OS lock |
| Interrupted intake | Re-run `worker IMPORT_ID`; recovery is capped at three attempts. Correct rejected/failed inputs and submit under a new key |
| Interrupted indexing | Re-run `index-run RUN_ID`; verified checkpoints are reused |
| CodeQL failure or timeout | Inspect `codeql-status` / `scan-report`, local diagnostics, tool and query availability before explicitly starting a new attempt |
| No current report | Publish the latest stored attempt, or intentionally select an exact ID / latest-completed envelope |
| Integrity failure | Preserve state for investigation; restore a verified backup or capture a new authorized run, rather than altering digests |
| Unknown/exhausted triage budget | Inspect `triage-report`; no automatic refund or budget increase exists |
| Disk filling | Stop new work and inspect storage. Automatic artifact cleanup is not implemented; do not delete referenced artifacts |

For a local backup, stop all TraceProof writers, copy the whole state directory (including SQLite sidecar files and artifacts), and keep tool/query/configuration provenance separately. Do not copy only the database during active writes. Restore to another local directory, run `init` as appropriate, verify snapshots and retrieve exact reports before relying on it. This is local operational guidance, not a production backup/restore qualification.

No explicit pause/cancel controls exist yet. `worker --max-items` bounds intake work; rerunning resumes supported checkpoints. There is no background all-stage scheduler: running `worker` captures archives, not the entire security pipeline. Do not infer 1,000-repository/day capacity from this POC.

## Further reference

Use `COMMAND --help` for exact arguments and pagination flags. [Slice contracts](../README.md) document version-specific limits; the [implementation plan](../plans/implementation-plan.md) tracks upcoming capabilities. The API companion guide is scheduled with the first hosted API and will add HTTP authentication, submission/polling, retry and error workflows to its OpenAPI reference.

## Initial Java static profile (Slice 37)

`codeql-extract`, `scan-run` and `scan-import` accept `--language java`; Python remains
the default. Supply an installed Java CodeQL query to analysis or the scan runner.
Each invocation selects one language; there is no automatic multi-language fan-out.
Reports retain that language and an inventory of other detected source languages.

This first Java profile supports dependency-free source using build mode `none`. It
rejects Maven/Gradle/Ant build descriptors, wrappers, JARs and Kotlin inputs. Spring,
external dependencies and generated code are not qualified. Java semantic indexing
and LLM evidence support are still pending, so Java reports remain **incomplete**,
even when CodeQL succeeds. Retrieve them using the exact report ID or latest-attempt;
`latest-completed` requires static review readiness and will not select them.

The repeatable local acceptance script uses a new output directory:

```sh
uv run python scripts/validate_java.py /path/to/java-queries/Security/CWE/CWE-089/SqlConcatenated.ql work/java-acceptance
```

It checks a JDBC concatenation fixture (one candidate) and a prepared-statement
fixture (zero), preserves incomplete readiness, and makes no model calls. These
fixtures do not establish repository security or measured recall.

### Java syntax coverage (Slice 38)

After `uv sync`, Java scan-run/scan-import automatically build a bounded syntax index.
A blocked syntax gate stops the runner before extraction and returns per-file statuses.
Standalone codeql-extract records syntax coverage but can still attempt extraction;
inspect the retained scope. Successful reports expose the index in language_scope.
No new migration or command is required. Syntax parsing does not establish Java
semantic or Spring support; readiness remains incomplete. See Slice 38 for limits.

### Spring annotation observations (Slice 39)

New Java indexes include `framework_observations` in the retained syntax index.
Each observation identifies its file/hash, annotation line and declaration target.
The first 200 matching annotation names are returned; inspect total/truncated.
A Spring namespace hint is not proof of runtime binding or an externally reachable
endpoint. Wildcard imports remain unresolved. No Java LLM policy or build-profile
support is enabled by these observations. Reusing an old report returns its original
contents; a new scan uses the versioned parser and retains fresh observations.

### Source-only Spring acceptance (Slice 40)

Run `uv run python scripts/validate_spring.py QUERY_PATH NEW_OUTPUT_DIRECTORY` with
an installed Java `SqlTainted.ql`. The suite checks vulnerable/fixed/foreign-annotation
controllers and malformed source. Outputs include validation.json, exact JSON/HTML
reports and a source-containing vulnerable evidence bundle. No model calls or Spring
builds run. A retained modeled path is not proof of deployed reachability. Java
readiness remains incomplete; Maven/Gradle and Java LLM policies are still pending.

### Java SQL advisory gate (Slice 41)

Gate 4 enables only java/sql-injection with complete small-file Java context,
explicit Spring RequestParam and executeQuery syntax on retained flow endpoints.
It supports needs_review with unknown guards; Java false-positive suggestions cannot
pass yet. Build a new bundle to retain full Java files of at most 40 lines within
existing byte limits. Larger/partial context stays insufficient. Old bundles and
reports remain unchanged; old triage keys may conflict across gate versions.
Use check-evidence for a local recheck without model spend. Existing provider,
classification and budget requirements apply to new triage. Java reports remain
incomplete; passing evidence is advisory and never confirms or suppresses a finding.

### Java context expansion (Slice 42)

Gate 5 can combine same-snapshot/file/hash excerpts into complete Java context.
Use the existing expand-bundle workflow to supply missing ranges, then check-evidence
against the new bundle. Missing lines or conflicting overlaps fail conservatively.
All expansion byte, range, depth and snippet limits still apply; no automatic model
calls occur. This supports larger files within those limits, but does not supply missing
flow steps or enable Java negative advice. Gate-version changes may conflict with old
triage keys; preserve uncertain calls rather than retrying them under new identities.

### Maven/Gradle layouts without builds (Slice 43)

Use `--language java --java-profile source-only` on codeql-extract, scan-run or
scan-import. CodeQL receives a verified Java-only copy: descriptors, wrappers, JARs,
Kotlin and other files are omitted. Inspect omitted-file counts and unresolved dependency/
generated-code coverage in language_scope. This is not a qualified Maven/Gradle build
or an OS/network sandbox. Default dependency-free behavior is unchanged. Batch skips
are profile-specific, so switching profiles may perform a fresh scan. No migration.

### Automatic language selection (Slice 44)

`--language auto` works on extraction, scan-run and scan-import. Exactly one detected
source language must be present and supported (Python/Java); mixed and unsupported
inventories require an explicit choice. Python remains the default when omitted.
Supply the correct query yourself; auto does not choose queries or run all languages.
For Java build layouts, add `--java-profile source-only` explicitly. Reports retain
whether language selection was automatic. scan-import applies one query across its
page, so group repositories by query applicability. No migration or build execution.

### Initial C# scanning (Slice 45)

Select --language csharp (or auto for a C#-only snapshot) and provide a compatible
C# query plus --allow-csharp-downloads. CodeQL may download an SDK and access NuGet;
without the opt-in, extraction is blocked. Only .cs files enter the copied source tree.
Project files, binaries and Razor views are omitted. Reports remain incomplete,
and C# LLM triage is unsupported. Classic ASP.NET misses the fixture without matching references; Slice 46 below
resolves it for the pinned net48 profile. Broader ASP.NET coverage remains unqualified. See Slice 45 for reproduction and bank prerequisites.

### Pinned C# dependencies (Slice 46)

Use --csharp-dependency-profile PATH with C# extraction/scan commands. SDK and reference
files are verified against the manifest; see Slice 46 for pin_csharp_dependencies.py.
The local working example is work/slice46-dependencies/profile.json. The matching net48
profile resolves the known classic fixture miss. Select profiles matching the target
framework; this does not qualify arbitrary projects. SDK/CodeQL version mismatches fail.
Profile changes prevent reuse of an earlier profile's scan attempt.

For macOS offline extraction, add --csharp-offline and omit --allow-csharp-downloads.
This requires the pinned profile. The app checks and applies network denial to SDK/
CodeQL version inspection and extraction, including child processes. Failure to establish
isolation blocks extraction; there is no network fallback. Successful extraction records
network_denial_verified=true. This option does not isolate query execution or LLM calls,
and is not a filesystem/build sandbox. Linux is unsupported by this option and fails
closed. The earlier explicit download opt-in remains available for other local runs.
See Slice 47 for validation and reproduction.
Mount SDK/reference directories read-only in deployment and give each scan writable
scratch. The macOS SDK is not portable to a Linux/OpenShift worker. Reports remain
incomplete and C# LLM advice is still unsupported. No migration.

### Pinned Java JAR profiles (Slice 50)

Use --java-dependency-profile PATH on codeql-extract, scan-run or scan-import with
Java (or auto selecting Java). scripts/pin_java_dependencies.py creates a versioned
manifest of approved local Maven-layout JARs; see the container operator guide. The
profile is validated before extraction and rechecked afterward. It participates in
scan reuse and report comparison. CodeQL version 2.27.0 is the qualified interface.

Supplying a profile does not enforce offline execution. CodeQL can infer additional
artifacts; keep network disabled in the runner when scanning offline. The container
Spring fixture uses a six-JAR pinned profile; this is not broad Spring qualification.
No Maven/Gradle builds or live LLM calls are introduced. No migration.

### C# SQL advisory evidence (Slice 56)

Gate 6 enables advisory review for `cs/sql-injection` when complete bounded C# source
contains an explicit ASP.NET Core FromQuery parameter and a CommandText assignment
anchored to the endpoints of a complete retained CodeQL thread. It supports the
qualified Core MVC/minimal API fixture shapes. Classic FromUri, implicit MVC binding,
raw request access, alternate SQL APIs and guard counterevidence remain unqualified.

Use the existing bundle-build, check-evidence and triage workflows. New bundles use
builder 5 and retain complete C# files up to 40 lines within existing byte budgets.
Larger files require consistent evidence expansions covering every line; reconstructed
context is capped at 16 KiB. Missing context, parser failure, conditional compilation,
ambiguous imports/aliases and local FromQuery lookalikes fail closed. A passing gate
checks quoted syntax and recorded flow consistency; it proves neither runtime request
binding nor exploitability. C# false-positive advice cannot pass this gate.

Provider classification, consent, token budgets and model configuration still apply.
No provider is enabled automatically. Old bundles/reports remain immutable; build a
new bundle to use the new context policy. Existing triage keys may conflict across
gate versions; use a new request key. Reports remain incomplete and findings remain
unreviewed until the existing operator-review workflow is used. This supersedes earlier
blanket statements that all C# triage is unsupported; support is narrow and advisory.

### Classic MVC/Web API advisory evidence (Slice 57)

Gate 7 extends `cs/sql-injection` to direct public classic Controller/ApiController
classes and public instance HttpGet actions with string parameters. MVC parameters
must have no binding attributes; Web API parameters must carry exactly FromUri.
Qualified namespace spellings or explicit matching imports are required. Private,
static, abstract, overridden or generic action shapes, NonAction/other method
attributes, mixed MVC/Core imports and local framework-name shadows are unqualified.
This is a narrow syntax policy, not a resolved model of all classic request binding.

Use the same bundle and triage commands. Complete bounded context and the entire
retained CodeQL path remain required. CommandText is the only qualified sink form;
unknown guards remain explicit and negative advice cannot pass. No request is confirmed
or finding suppressed automatically. Existing reports/bundles remain immutable, and
new triage requests use gate 7. The capability label is aspnet_sql_review_v2; report
comparison flags a change from the earlier Core-only policy. No migration.

### JavaScript and TypeScript source-only scans (Slice 58)

Use `--language javascript` or `--language typescript` on `codeql-extract`, `scan-run`
and `scan-import`. Both use CodeQL's JavaScript extractor, but keep separate selection,
coverage and report identities. Python remains the default. `--language auto` selects
one detected supported language; mixed JS/TS repositories require explicit selection
and report the other language as unselected. Consolidated mixed-language scans remain
future work.

```bash
uv run traceproof scan-run RUN_ID /absolute/approved-CodeInjection.ql --language javascript
uv run traceproof scan-run RUN_ID /absolute/approved-CodeInjection.ql --language typescript
```

The fixture-qualified query is javascript-queries 2.4.5's
Security/CWE-094/CodeInjection.ql (`js/code-injection`). Approved compatible `.qls`
suites can be supplied in the same position, with the limits described earlier.

JavaScript extraction copies .js/.jsx/.mjs/.cjs files; TypeScript copies
.ts/.tsx/.mts/.cts files. Copies are verified against the captured snapshot before
and after extraction. Package manifests, tsconfig, source maps, HTML and files from
the other language are omitted. No npm install, package hooks or application build is
requested. This intentionally limits module resolution, especially for mixed projects.

The initial fixtures cover an Express request query reaching eval and a fixed JSON
serialization counterpart. TypeScript uses explicit type annotations, but this does
not establish type-checking or dependency resolution. Browser frameworks, asynchronous
flows, JSX/TSX framework coverage and generated/source-map attribution are unqualified.
Reports remain incomplete, with semantic indexing and LLM evidence unsupported for
JS/TS. Other static candidates remain available for manual review; the configurable
exploratory triage mode is still planned, not enabled by this language addition.

### Scanner provenance in static-attempt JSON

New `scan-report` JSON includes `scanner`, `prepared_input`, and `rule_entry` metadata.
CodeQL and bounded Joern profiles are available through scan-run/scan-import. The entry hash does not cover imported
queries or packs; capability flags do not guarantee that a finding includes a complete
flow. Historical reports retain their original fields. `scan-import` skipping is a retry
safeguard, not proof of unchanged tools/rules; use `--rescan` when those change.

### Experimental Joern Java discovery

After normal CSV/archive intake creates a source run, use the explicitly experimental
bounded-query path (Joern 4.0.625 operator installation required):

```sh
uv run traceproof joern-java-discover RUN_ID /absolute/path/to/joern-cli --timeout 180
uv run traceproof scan-report REPO_ID --attempt-id ATTEMPT_ID
uv run traceproof publish-report REPO_ID --run-id RUN_ID --attempt-id ATTEMPT_ID
uv run traceproof get-report REPO_ID --format html
```

This selects only Java source and follows String parameters annotated with the fully
qualified Spring `RequestParam` on public `GetMapping` methods into the graph signature
`java.sql.Statement.executeQuery:java.sql.ResultSet(java.lang.String)`. Method and parameter
names are unrestricted. Graphs, logs, original JSON, normalized SARIF and candidates are
stored under the attempt. This is a bounded discovery model, not a general Spring scanner:
other routes, parameter types, JDBC APIs, reflection and application bean wiring are not
qualified. Fully qualified graph names are static observations, not proof of runtime type
identity or library authenticity. Results remain partial/discovery-only and cannot use
qualified CodeQL triage. Other languages, builds and dependencies are omitted. Query customization
and automatic backend selection are not exposed yet.

Timeout applies independently to preparation and analysis; failure details identify the
stage and its local log. Requested JVM heap is 2 GiB, not a total memory limit. Network
isolation is not enforced; use synthetic/local POC inputs. The installation version layout
is checked, but installation contents are not cryptographically pinned by the command.
The earlier release download checksum validation is documented in Slice 63.

`scan-report` and published report JSON include scanner identity and limitations. Shared
HTML/Markdown reports retain that metadata. Historical reports remain immutable. No
migration or model key is required. Standard `scan-run` remains CodeQL-only.

Joern `discovery_coverage` now distinguishes modeled flows, absent modeled sources,
absent modeled sinks, and endpoints with no recorded flow. It also lists selected Java
files absent from the graph inventory. A represented file is not proof that every
construct parsed correctly. Parser diagnostic counts remain unknown (`null`) until their
reporting is qualified. `process_stages_completed: true` means both tools exited zero;
`execution_complete` remains false and successful discovery remains partial. Published
JSON/HTML/Markdown reports retain this coverage block.

`joern_diagnostics` adds bounded observations of Joern 4.0.625 preparation/analysis logs:
recognized warning/error event counts, known parser-problem files, unmapped parser events,
and unavailable/truncated log states. Repeated warnings count as events but affected files
are deduplicated. No source excerpts or raw diagnostic messages enter the summary.
An empty log does not prove complete parsing; authoritative diagnostic counts stay null.
A scan may retain valid candidates while also reporting files that failed parsing.

### Experimental repaired Joern C# discovery

After intake captures an immutable snapshot, run the opt-in profile:

```sh
uv run traceproof joern-csharp-discover RUN_ID \
  /absolute/path/to/joern-cli /absolute/path/to/csharp-repair-build --timeout 180
uv run traceproof publish-report REPO_ID --run-id RUN_ID --attempt-id ATTEMPT_ID
uv run traceproof get-report REPO_ID --report-id REPORT_ID --format html > report.html
```

The repair build is produced by scripts/build_joern_csharp_repair.py, as documented in
scripts/joern/csharp-repair/README.md. Supply trusted operator tools, never a repair build
or classpath from a scanned repository. The command reconstructs the classpath from the
build receipt and rechecks its recorded jars/classes/source before and after scanning;
these hashes detect changes but do not authenticate who supplied the tools. This initial
implementation rehashes dependencies per scan, so it is not a throughput optimization.

Coverage is intentionally limited to the named Lookup parameter name flowing to a
CommandText assignment RHS. It is not general ASP.NET discovery. Only .cs source is copied;
no project build or dependency restore runs. Complete paths need uniquely validated
source spans before publication. Unsupported paths are retained in flows.json and
source-mapping.json, with counts exposed in the scan and published JSON report.

Every successful attempt remains partial and non-adjudicated, including zero candidates.
The fixed packaged rule has its own identity and cannot inherit CodeQL triage qualification.
Framework syntax facts remain audit observations. This command does not enforce OS network
isolation; use the restricted container deployment pattern. Automatic pipeline selection,
broader C# rules and production qualification are not enabled by this opt-in command.

## Experimental Python discovery with Joern

After archive intake, run:

```sh
traceproof joern-python-discover RUN_ID /trusted/joern-cli --timeout 180
```

This opt-in profile selects the `input` parameter of methods named `lookup` and the first
argument of calls named `system`. It is a bounded integration profile, not a general
Python web-framework scanner; matching a call name does not authenticate `os.system`.
Only `.py` source is copied. No repository scripts or dependency installation are run.
Use normal scan/report retrieval and publication commands for its durable results.
Reports remain partial/non-adjudicated even when there are no candidates; Joern evidence
does not inherit qualified CodeQL triage policies. Trusted pinned Joern 4.0.625 tooling
is required. The CLI itself does not enforce OS network isolation.

## Experimental JavaScript and TypeScript discovery with Joern

```sh
traceproof joern-javascript-discover RUN_ID /trusted/joern-cli --timeout 180
traceproof joern-typescript-discover RUN_ID /trusted/joern-cli --timeout 180
```

Each explicit command uses its own rule identity and copies only `.js` or `.ts` files,
respectively. Mixed-language flows, JSX/TSX, framework models and project configuration
are outside this initial profile. Sources are parameters named `input` in methods named
`lookup`; sinks are the first arguments of calls named `eval`. These names do not prove
HTTP input or builtin eval identity. Reports use the normal durable retrieval/publication
workflow, remain incomplete, and carry no qualified triage eligibility. No package
installation, application build or repository script execution is requested. Trusted
Joern 4.0.625 is required; network isolation must be supplied by the runtime.

## Experimental Go discovery with Joern

```sh
traceproof joern-go-discover RUN_ID /trusted/joern-cli --timeout 180
```

The bounded profile selects `lookup(input)` parameters and argument 3 of calls named
`Command`, matching the assessed shell-command fixture. It does not authenticate
`os/exec.Command`, prove shell execution, or cover all command argument positions.
Only `.go` sources and `go.mod` metadata are copied; graph coverage counts source files
separately from metadata. Source and metadata hashes are checked before and after scanning.
Go proxy/checksum downloads are disabled and automatic toolchain fetching is disabled.
The CLI itself does not provide OS network isolation. Frameworks, dependencies, cgo,
build tags and advanced semantics remain unqualified. Use normal durable report retrieval
and publication; results remain incomplete and qualified Joern triage stays unsupported.

## Experimental Rust discovery with Joern

```sh
traceproof joern-rust-discover RUN_ID /trusted/joern-cli /trusted/rust --timeout 180
```

Supply a standalone Rust toolchain containing `bin/rustc`, `bin/cargo` and matching
`rust-src`. The Linux acceptance image pins Rust 1.98.1; the local command checks layout,
not tool publisher authenticity. Tooling must be operator-controlled.

The initial profile accepts a root `Cargo.toml` with only `[package]` and one explicit
`[[bin]]`. Package fields are name/version/edition and optional `build=false`; the binary
has name and a source-relative `.rs` path. Dependencies, workspaces, custom build hooks
and other manifest settings are rejected before creating a scan. This is deliberately
limited preparation support, not support for arbitrary Cargo projects.

TraceProof copies `.rs` files and generates restricted Cargo metadata with build scripts
and automatic target discovery disabled. Repository Cargo configuration/toolchain files
are not copied. Cargo runs offline with a per-attempt home. OS network isolation still
requires the restricted runtime. Generated metadata has its own digest in the scan report;
it does not replace the original archived source manifest.

The query selects `lookup(input)` parameters and argument 1 of calls named `arg`. It does
not authenticate `std::process::Command`, prove shell execution, or detect all Rust memory
safety issues. Reports remain partial/non-adjudicated and qualified triage is unsupported.
Use the normal durable scan/report retrieval and publication commands.

## Experimental C/C++ discovery with Joern

```sh
traceproof joern-c-discover RUN_ID /trusted/joern-cli --timeout 180
traceproof joern-cpp-discover RUN_ID /trusted/joern-cli --timeout 180
```

C selects `.c` and `.h`; C++ selects `.cpp`, `.h` and `.hpp`. Other extensions and
mixed C/C++ flows are outside these initial profiles. Included headers are source files
for inventory purposes. No compilation database, application build or dependency
installation is requested. Build configuration and preprocessor coverage remain unqualified.

Both profiles select `lookup(input)` parameters and argument 1 of calls named `system`.
Call names do not authenticate the library function or prove runtime reachability.
C++ acceptance covers the common C/C++ subset, not classes, templates or virtual dispatch.
These queries do not constitute memory-safety detection coverage. Normal durable scan
retrieval and HTML/JSON publication apply; reports remain incomplete and qualified triage
unsupported. Trusted pinned Joern tooling and external runtime isolation are required.

## Joern through the main scan workflow

```sh
traceproof scan-run RUN_ID --engine joern --joern-home /trusted/joern-cli --language auto
traceproof scan-import IMPORT_ID --engine joern --joern-home /trusted/joern-cli \
  --language auto --limit 10
```

Omit the positional CodeQL query argument for Joern: only packaged profiles are accepted.
CodeQL remains the default engine and still requires its query argument. `--language auto`
selects one detected supported source language; mixed-language snapshots require an
explicit language and retain partial coverage. Supported Joern profiles are Python,
Java, C#, JavaScript, TypeScript, Go, Rust, C and C++. Their existing scope restrictions
still apply. Headers alone do not select C versus C++ automatically.

For C# also supply `--joern-repair-dir /trusted/csharp-repair`; for Rust supply
`--rust-home /trusted/rust`. Both paths may be provided for a mixed-language import;
only the applicable one is passed to each scan. Each individual snapshot still requires
one auto-detected language or an explicit selection. Missing required tools become
explicit row errors in batch scans. CodeQL preparation/dependency flags cannot be used
with the Joern engine. Keep `--threads 2 --ram-mb 2048` at their current defaults; Joern
requests a 2 GiB JVM heap, while CPU/memory isolation is the runtime's responsibility.
`--extraction-timeout` and `--query-timeout` apply to their separate Joern stages.

The workflow publishes the exact new attempt, including a failed scan's incomplete
report. It makes no LLM calls and never promotes Joern evidence to qualified triage.
Batch scanning retains pause/cancel and pagination behavior. By default it skips an
existing Joern attempt for the same run and language, including failed attempts. This
only suppresses retries; it does not validate unchanged tooling or reuse findings as a
new result. Use `--rescan` after a failure or tool/profile change. CodeQL attempts do not
suppress Joern scans. A direct scan-run always requests a new attempt.

This slice connects the local CLI/main orchestration workflow. It does not register
Joern with the lower-level CodeQL prepared-database API or add an API scan-launch route.
Existing report retrieval APIs continue to serve published results.

## Joern benchmark coverage audits

The existing schema-1 evaluation plan remains the qualified Python CodeQL location-proxy
contract. For Joern, use a schema-2 plan with these fields:

```json
{
  "schema_version": "2",
  "mode": "discovery_coverage_audit",
  "engine": "joern",
  "manifest_sha256": "<benchmark manifest SHA-256>",
  "query_sha256": "<published report query SHA-256>",
  "scanner_version": "4.0.625",
  "profile": "standard",
  "rule_ids": ["traceproof/joern-rust-lookup-arg-v1"],
  "reports": [{"repo_id": "example", "report_id": "<published report ID>"}]
}
```

Use real 64-character digests in place of placeholders. One packaged Joern rule per plan
is supported; evaluate different profiles separately. All nine current profile identities
are recognized. CWE associations describe query intent and do not qualify detection.
The existing benchmark manifest/label contracts and snapshot/file integrity checks apply.

```sh
traceproof benchmark-evaluate manifest.json labels.json plan.json --format html
traceproof benchmark-publish manifest.json labels.json plan.json
```

These evaluator-only operations do not scan or call models. Audit output uses evaluator
version 3, retains all labels in the denominator, and explicitly marks them not_evaluable
for currently unqualified Joern discovery profiles. Recall values, confirmed recall and
precision remain null; no zero-recall or false-positive conclusion is justified.
Candidates remain unjudged. Scanner/version/query/language mismatches are disclosed;
missing reports remain visible. Comparison rejects incomplete audits rather than showing
an improvement delta. Existing immutable CodeQL scorecards remain readable and unchanged.

Use JSON or repositories-csv for scanner identity, source language, graph inventory and
scanner limitations alongside scope_gaps. HTML/Markdown and summary/label/weakness CSV
formats remain available. JSON nulls export as blank numeric CSV cells. The audit is a
coverage-readiness report, not a measurement of discovery quality; broader models and
adjudicated evaluation remain necessary before reporting bank-portfolio precision/recall.

## Flask request-to-shell discovery profile

```sh
traceproof scan-run RUN_ID --engine joern --joern-home /trusted/joern-cli \
  --language python --joern-profile python-flask-system-v1
```

The same option works on scan-import. The standalone joern-python-discover command uses
`--discovery-profile python-flask-system-v1`. Omitting it retains the earlier fixture
profile. Batch retry skipping distinguishes the selected profile; a previous default
Python scan does not suppress this Flask scan. Use --rescan for changes within a profile.

Sources are single-line `request.args.get("key")` or `request.form.get("key")` calls;
sinks are single-argument `os.system(value)` calls. A bounded isolated AST parser requires
single top-level imports from Flask and os (aliases supported) and rejects obvious
rebinding, conflicting/wildcard imports and local flask/os module shadows. Endpoints are
joined to unique same-name Joern calls at their source file/line; ambiguous joins are
withheld. Function names and parameter names are unrestricted.

This is syntax-informed discovery, not proof of module identity, HTTP reachability or
absence of dynamic monkeypatching. Multiline accesses, get defaults/dynamic keys,
subprocess APIs, other Flask inputs and frameworks remain outside this profile.
Raw graphs may contain synthetic intermediate nodes. Endpoint locations are checked in
fixtures; synthetic nodes are not claimed as exact source snippets. Reports remain
partial and qualified triage remains unsupported. Published JSON includes discovery_profile
and endpoint_audit file-status counts/digest; full endpoints.json is retained with the scan.
The new rule is accepted by the benchmark coverage-audit mode without qualifying recall.

## Express request-to-eval discovery profile

```sh
traceproof scan-run RUN_ID --engine joern --joern-home /trusted/joern-cli \
  --language javascript --joern-profile express-request-eval-v1
```

Use `--language typescript` for TypeScript or `auto` for a repository containing a
single supported source language. `scan-import` accepts the same profile. Standalone
`joern-javascript-discover` and `joern-typescript-discover` use
`--discovery-profile express-request-eval-v1`. Default profiles remain unchanged.

The profile selects inline callbacks passed as the second argument of Express get/post
registrations recognized by Joern. Sources are field reads of the first callback
parameter: `req.query.code`, `req.body.expression`, or `req.params.expression`, with
arbitrary parameter and field names. Sinks require Joern's builtin `eval` signature.
The graph supplies the intervening flow, including supported ES-module cross-file calls.
No repository packages are installed and no application code is executed.

This is bounded discovery, not authenticated Express/builtin identity or demonstrated
HTTP exploitability. Import aliases for the Express factory are not qualified (the
initial alias fixture was missed). Routers, middleware chains, named callbacks,
destructuring, computed/deeper property accesses, JSX/TSX, mixed JS/TS repositories,
project configuration and dependency resolution are outside acceptance. Dynamic
rebinding/mutation and sanitization semantics are not qualified. Only `.js` or `.ts`
sources for the selected language are copied.

Published reports remain partial, with the selected discovery_profile and limitations.
Zero candidates cannot establish a clean result. These rules are accepted by benchmark
coverage audits, with recall/precision unknown and qualified triage unsupported. Batch
retry skipping distinguishes profiles; use `--rescan` after changes within a profile.

## Go HTTP form-to-shell discovery profile

```sh
traceproof scan-run RUN_ID --engine joern --joern-home /trusted/joern-cli \
  --language go --joern-profile go-http-shell-v1
```

The same profile works with `scan-import` and `--language auto` for a single-language
repository. The standalone `joern-go-discover` command accepts
`--discovery-profile go-http-shell-v1`. Omitting the profile retains the default.

Sources require Joern's `net/http.Request.FormValue` or `PostFormValue` graph signature.
Sinks require `os/exec.Command` with exactly three arguments: a literal `sh`, `bash`,
`/bin/sh` or `/bin/bash`; literal `-c`; then the command text. Joern must record a flow
from the request input to that third argument. Ordinary process arguments such as
`exec.Command("printf", "%s", value)` are outside this rule, not declared safe by it.
Direct and supported cross-package flows do not depend on fixture function names.

Command construction is sufficient for a candidate: the profile does not prove that
Run/Start/Output is called or that a route is registered and reachable. Import aliases
and PostFormValue have bounded fixture acceptance. Dependency/module identity, dynamic
behavior and sanitizer semantics are not qualified. URL.Query, headers, JSON bodies,
CommandContext, other shells/flags, raw-string shell literals, concatenated or variable
shell names and additional arguments are outside acceptance. Only `.go` sources and
go.mod are copied; dependencies and builds are not executed.

Reports retain partial/discovery-only status, rule/profile/query identity and limitations.
Qualified triage is unsupported. Benchmark coverage audits accept the rule as a CWE-78
candidate scope, with recall/precision unknown. Zero candidates cannot establish a clean
result. Batch retry skipping distinguishes profiles; use `--rescan` for changed inputs
or models within a profile. No database migration or LLM key is needed for discovery.

## C/C++ command-line-to-system discovery profile

```sh
traceproof scan-run RUN_ID --engine joern --joern-home /trusted/joern-cli \
  --language c --joern-profile c-family-argv-system-v1
```

Use `--language cpp` for the supported C-style C++ subset, or `auto` for a single-language
repository. `scan-import` accepts the same profile. Standalone `joern-c-discover` and
`joern-cpp-discover` accept `--discovery-profile c-family-argv-system-v1`. Default profiles
remain unchanged.

The source is an indexed read of global main's second parameter, declared as char**
or char*[] and a positive decimal literal index, for example `arguments[1]`. Parameter
names are unrestricted. Joern must link the indexed identifier to that parameter and
record a flow to argument one of the unqualified system graph signature. A repository
definition named system causes all sinks to be withheld conservatively.

C++ uses Joern's unresolved-namespace system signature; C uses its unqualified system
signature. This profile does not authenticate libc identity or runtime exploitability.
Argument zero, variable/hexadecimal indices, pointer aliases/arithmetic, wide-character
entry points, qualified std::system calls, build macros/configuration and sanitizer
semantics remain outside acceptance. C++ classes/templates/virtual dispatch and
memory-safety vulnerabilities are not covered. Only `.c/.h` or `.cpp/.h/.hpp` files are
selected; `.cc/.cxx` and mixed C/C++ flows remain outside this bounded profile.

Published reports remain partial/discovery-only and include profile/query identity and
limitations. Zero candidates cannot establish a clean result. Qualified triage is
unsupported; benchmark coverage audits accept the new CWE-78 rule scopes with unknown
recall/precision. Batch retry skipping distinguishes profiles; use `--rescan` for changes
within a profile. No migration, source build or LLM key is required for discovery.

## Rust environment-to-shell discovery profile

```sh
traceproof scan-run RUN_ID --engine joern --joern-home /trusted/joern-cli \
  --rust-home /trusted/rust --language rust --joern-profile rust-env-shell-v1
```

`scan-import` accepts the same options, including `--language auto` for a single-language
repository. Standalone `joern-rust-discover` accepts
`--discovery-profile rust-env-shell-v1`. The trusted Rust toolchain and existing strict,
dependency-free, single-binary Cargo contract are still required. Defaults remain unchanged.

Sources require the std::env::var graph signature and a literal key. Sinks require the
standard-library Command::arg graph signature in a chain constructed as
`Command::new("sh").arg("-c").arg(value)`. Literal bash, /bin/sh and /bin/bash are also
modeled. Up to four address/dereference graph wrappers per receiver are stripped to
identify the chain; the graph must supply the flow from the environment value to the
command-text argument. No synthetic dataflow edges are added.

Command construction does not prove execution, and an environment value is not necessarily
attacker-controlled. Graph identities and sanitization semantics remain unqualified.
Command-line args, var_os, dynamic environment keys, split builder variables, args arrays,
other shells/flags and advanced Rust/Cargo/framework features are outside acceptance.
Ordinary non-shell arguments are outside this rule, not declared safe by it.

Reports remain partial/discovery-only and preserve profile/query identity and limitations.
Qualified triage remains unsupported; coverage audits recognize the CWE-78 candidate
scope with precision/recall unknown. Zero candidates cannot establish a clean result.
Batch retry skipping distinguishes profiles; use `--rescan` for changes within a profile.
No migration or LLM key is needed. Generated Cargo metadata continues to disable build
hooks and automatic targets; source dependencies are not installed.

## Explicit Joern Spring evidence review

Fresh Java/Spring Joern scans now pin the native flows.json digest. Building a bundle
adds a joern_native_audit that checks the pinned scanner/query, native-to-SARIF consistency,
unique path selection and exact native code on snapshot-bound source lines. Older scans
without the native digest remain readable but need a new scan to qualify for this audit.

```sh
traceproof build-bundle ATTEMPT_ID CANDIDATE_FINGERPRINT
traceproof check-evidence BUNDLE_ID decision.json \
  --review-policy joern-spring-review-v1
```

The decision uses the existing strict claim schema: needs_review with quoted source, sink,
flow and guard claims; unknown guard effectiveness is permitted. A passing result means
supported_for_review, not confirmed vulnerability, framework identity or exploitability.
Full consistent source context is required for all retained path files. The native gate
accepts one unambiguous path of two to seven single-line source-matching nodes; truncation,
synthetic/multiline code, changed provenance and missing context withhold review eligibility.
Java negative verdicts remain unsupported. Existing bundle size/context limits still apply.

This command invokes no provider, spends no model tokens, and does not persist a triage
verdict or suppress findings. Without the explicit policy option, Joern remains unsupported
by check-evidence's default gate. The main Joern scan pipeline and automatic triage registry
also remain discovery-only; this policy is not an automatic promotion or a benchmark change.
Bundle schema version remains 1 with builder version 7 and additive native audit metadata;
historical immutable bundles remain readable. No database migration is required.

## Opt-in budgeted Joern Spring advisory

After scanning and building a fresh audited Spring bundle, use the existing run budget
and model configuration with an explicit review policy:

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof triage BUNDLE_ID model.json advisory-key \
  --review-policy joern-spring-review-v1 --replay response.json
```

Use a replay-provider model configuration and a response matching the existing Reply /
Decision schema for offline testing. A replay response tests orchestration; it does not
measure model detection quality. Configured token rates exercise the ledger even for replay,
so accounted amounts in these tests are simulated, not external charges.

`triage-attempt REPO_ID ATTEMPT_ID model.json BATCH_KEY` accepts the same explicit policy
and replay options, with existing offset/limit controls. Each candidate gets its own
preflight and budget reservation. Batch keys distinguish default and explicit policies;
single-item reuse of a key with changed policy/request/preflight raises a conflict.
Retries return the existing ledger entry without another invocation. Budget/request limits
and uncertain-call reservation retention remain in force. Blocked rows count toward the
request limit but reserve/charge zero when blocked by evidence or cost preflight.

Before invoking a provider, TraceProof requires the native audit, complete source context,
ordered flow and modeled Spring/SQL endpoint syntax. Rejected preflight records
incomplete_evidence and makes no provider call. Returned needs_review claims must still
pass the explicit policy; fabricated or negative claims abstain. A passing advisory is
unverified and cannot suppress a finding. The report remains partial/incomplete.

The existing OpenAI, Anthropic and local Ollama adapter paths also accept the explicit
policy, subject to their existing classification, endpoint, pricing, key and source-
transmission controls. Their prompt shapes are tested offline; no live model quality is
claimed by this slice. Omit --replay for a configured non-replay provider.

Use triage-report to retrieve the ledger, then publish a fresh repository report to include
the new advisory history. JSON history includes review_policy, engine_id, model/provider,
request identity, costs and simulated status; HTML remains shareable. Older published
snapshots are immutable. Report projection version is now 12; no database migration.

Without --review-policy, Joern triage remains unsupported. scan-run/scan-import remain
separate discovery steps with zero automatic model calls. This opt-in is exposed through
CLI/Python triage operations; HTTP API launch schemas have not been expanded in this slice.

## Scan and publish with an explicit advisory page

Configure the existing per-run budget first. For the default Java/Spring Joern profile:

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof scan-run RUN_ID --engine joern --language java \
  --joern-home /trusted/joern-cli \
  --advisory-config model.json --review-policy joern-spring-review-v1 \
  --advisory-key scan-advice --advisory-limit 1 --replay response.json
```

The replay response must match the candidate's evidence IDs and quotes; acceptance fixtures
provide deterministic examples. Use the existing non-replay provider configuration and
omit --replay for explicit live advisory, subject to the existing transmission controls.
This slice validates replay orchestration, not live model quality.

`scan-import IMPORT_ID` accepts the same advisory options. Every admitted run selected for
advisory scanning needs its own preconfigured triage budget. Missing budgets fail before
new extraction. Eligible pairs are default Joern Java with joern-spring-review-v1,
python-flask-system-v1 with joern-flask-review-v1, and express-request-eval-v1 with its
language-specific JavaScript/TypeScript policy, and default repaired C# with
joern-csharp-review-v1, go-http-shell-v1 with joern-go-http-review-v1, and
rust-env-shell-v1 with joern-rust-env-review-v1 (see below). Other engine/profile/policy
combinations reject these pipeline advisory options.

The pipeline publishes the discovery attempt first, processes one bounded candidate page,
then publishes a report for the same exact attempt including advisory history. Inspect
`advisory.status`, item states and `advisory.next_offset`; page_complete does not imply
all candidates or security analysis are complete. The overall status remains incomplete.
Failed scans skip advisory and still publish their scan report. Evidence/budget failures
and uncertain calls retain the existing ledger and abstention behavior.

`--advisory-offset` defaults to zero; `--advisory-limit` defaults to one and is capped at
100. These are candidate bounds per repository, separate from scan-import's repository
row offset/limit. Import pause/cancel is checked between repository rows; an already
started bounded advisory page is not interrupted by those dispatch controls.

Existing-attempt skips also skip advisory, even if the earlier scan had no advice. Continue
with `triage-attempt REPO_ID ATTEMPT_ID model.json scan-advice --review-policy
joern-spring-review-v1 --offset NEXT --limit N` and the appropriate replay/provider options,
then publish a new report. Use the same key to retain per-candidate idempotency. Do not
rescan solely to continue the next advisory page: an explicit rescan creates a new attempt
and can incur new charges under the same run budget.

`model_calls` counts adapter invocations in this operation, including replay; cached ledger
returns and blocked candidates count zero. `live_model_calls` excludes replay. Per-row
advisory metadata identifies provider and simulated status, and scan-import aggregates the
counts. No advisory options means unchanged discovery-only execution. HTTP API launch
schemas remain unchanged; the pipeline opt-in is currently exposed through CLI/Python.

### Joern Python/Flask advisory (Slice 99)

Use `joern-flask-review-v1` with the explicit `python-flask-system-v1` discovery profile:

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof scan-run RUN_ID --engine joern --language auto \
  --joern-home /trusted/joern-cli --joern-profile python-flask-system-v1 \
  --advisory-config model.json --review-policy joern-flask-review-v1 \
  --advisory-key flask-advice --advisory-limit 1 --replay response.json
```

The same flags work on scan-import; each admitted run needs its own budget. For an existing
attempt, use triage-attempt with `--review-policy joern-flask-review-v1`, then publish its
report. check-evidence and single-bundle triage also accept this policy. Existing-attempt
skips do not add advice; use triage-attempt for continuation rather than rescanning merely
to obtain another candidate page. Replay responses must match the current evidence IDs and
quotes. Live use omits --replay and follows the existing model/transmission configuration.

This policy covers bounded Flask args/form.get with one literal key flowing to os.system,
including accepted explicit aliases. It requires fresh native provenance, retained complete
source context and matching parsed endpoints. Other Python profiles/frameworks are not
eligible. Missing context/provenance produces incomplete_evidence without a model call;
inspect the review_preflight status and bundle gaps. A fresh scan may be necessary for
legacy attempts lacking native provenance, but cannot resolve every coverage limitation.

A needs_review response must quote the source call and the full os.system call, and include
recorded-flow evidence plus an unknown guard assessment. Quoting the sink argument alone
is insufficient. Generated intermediate expressions are tool observations, not literal
source or proof of reachability. False-positive dismissal and present-guard claims are
unsupported. Reports remain incomplete and unverified; replay advice is marked simulated.
Report IDs, JSON/HTML export, invocation counts and pagination follow the workflow above.

### Joern Express advisory for JavaScript/TypeScript (Slice 100)

Use a language-specific policy with the existing Express discovery profile:

| Detected/selected language | Discovery profile | Explicit advisory policy |
|---|---|---|
| javascript | express-request-eval-v1 | joern-javascript-express-review-v1 |
| typescript | express-request-eval-v1 | joern-typescript-express-review-v1 |

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof scan-run RUN_ID --engine joern --language auto \
  --joern-home /trusted/joern-cli --joern-profile express-request-eval-v1 \
  --advisory-config model.json --review-policy joern-javascript-express-review-v1 \
  --advisory-key express-advice --advisory-limit 1 --replay response.json
```

For TypeScript, replace the policy with joern-typescript-express-review-v1. Auto detection
still requires the selected policy to match the detected language. A mixed-language source
requires explicit language selection under the existing scan behavior; it does not produce
a combined JS/TS assessment. The same options work with scan-import, with per-run budgets.
For existing attempts use triage-attempt with the matching policy, then publish its report.
Existing-attempt skips also skip advice. Replay replies must match current evidence; live
use omits --replay and follows the existing provider and source-transmission controls.

The bounded gate recognizes a default Express import, const application factory, inline
get/post handler, static request.query/body/params field read and direct eval argument.
It requires complete retained context and literal native path nodes. Ambiguous endpoints,
obvious rebinding/shadowing, optional/computed request access, member eval and unsupported
framework patterns do not qualify. Quoting only the eval argument does not satisfy the
sink claim: quote the complete eval call. Guards must remain unknown; false-positive
dismissal and present-guard claims are unsupported. Passing advice is needs_review, with
incomplete/unverified scan status. Replay advice remains visibly simulated.

HTTP launch schemas are unchanged. Existing exact-report retrieval and JSON/HTML export
include the advisory history and policy identity for dashboard integration.

### Repaired Joern C#/ASP.NET advisory (Slice 101)

Use the default C# discovery profile and a trusted repair directory:

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof scan-run RUN_ID --engine joern --language csharp \
  --joern-home /trusted/joern-cli --joern-repair-dir /trusted/csharp-repair \
  --advisory-config model.json --review-policy joern-csharp-review-v1 \
  --advisory-key csharp-advice --advisory-limit 1 --replay response.json
```

Auto language detection is also supported. scan-import accepts the same options; each run
needs its own budget. For existing attempts use triage-attempt with
`--review-policy joern-csharp-review-v1`, then publish the report. check-evidence and
single-bundle triage accept the same policy. Existing-attempt skips also skip advice.
Live use omits --replay and retains the existing provider/transmission controls; replay
responses must match the retained evidence IDs and quotes.

This does not expand discovery beyond Lookup(name) flowing to a CommandText assignment.
Advisory requires recognized Core FromQuery or classic HttpGet source syntax, mapped native
spans, repair provenance and complete retained context. Quote the full source/assignment
line, not just the CommandText RHS. The sink is a syntax observation, not authenticated API
identity. Guards remain unknown; false-positive dismissal is unsupported.

Inspect incomplete_evidence and review_preflight, then the bundle's joern_native_audit for
details. native_mapping_limit means the native result exceeded 32 paths or 128 nodes for
bounded advisory reconstruction. Changing --advisory-limit does not bypass this per-result
bound. Candidates and their discovery reports remain available when advisory is withheld.
Legacy attempts lacking provenance may need a fresh scan, which may incur new costs.
Successful advice remains needs_review with an incomplete/unverified report. Existing
report retrieval and JSON/HTML export include the policy and advisory history; API launch
schemas are unchanged.

### Joern Go HTTP-to-shell advisory (Slice 102)

Use the explicit Go discovery and advisory policy pair:

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof scan-run RUN_ID --engine joern --language auto \
  --joern-home /trusted/joern-cli --joern-profile go-http-shell-v1 \
  --advisory-config model.json --review-policy joern-go-http-review-v1 \
  --advisory-key go-advice --advisory-limit 1 --replay response.json
```

scan-import accepts the same options and requires a budget per run. For existing attempts,
use triage-attempt with `--review-policy joern-go-http-review-v1`, then publish the report.
Single-bundle triage and check-evidence also accept this policy. Existing-attempt skips skip
advice too; use triage-attempt for continuation rather than rescanning solely to get another
page. Live use omits --replay and follows the existing provider/source-transmission controls.
Replay responses must match the current evidence IDs and quotes.

The gate recognizes literal-key FormValue/PostFormValue on a *http.Request function
parameter and exec.Command with a literal shell, -c, and command text. Simple import aliases
are supported; obvious shadows, unsupported imports, dynamic command shapes and ambiguous
endpoint lines are withheld. Quote the entire exec.Command call, not just its command-text
argument. Complete context and literal native path evidence are required. Inspect
review_preflight and the bundle's joern_native_audit when a call is blocked.

A recorded Command construction does not prove it executes or that its source handler is
reachable. Guard claims remain unknown; negative dismissal is unsupported. Advice remains
needs_review/abstain in an incomplete, unverified report, with replay visibly simulated.
Existing report retrieval and JSON/HTML exports include advisory history and policy identity;
HTTP launch schemas remain unchanged.

### Joern Rust environment-to-shell advisory (Slice 103)

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof scan-run RUN_ID --engine joern --language auto \
  --joern-home /trusted/joern-cli --rust-home /trusted/rust \
  --joern-profile rust-env-shell-v1 --advisory-config model.json \
  --review-policy joern-rust-env-review-v1 --advisory-key rust-advice \
  --advisory-limit 1 --replay response.json
```

The trusted Rust toolchain and existing dependency-free single-binary Cargo restrictions
still apply. scan-import accepts the same options with budgets per run. Existing-attempt
skips also skip advice; use triage-attempt with --review-policy joern-rust-env-review-v1
for continuation, then publish the report. check-evidence and single-bundle triage accept
the same policy. Replay replies must match current evidence; live use omits --replay and
follows the existing provider and source-transmission controls.

The bounded policy recognizes literal-key std::env::var (or a supported simple import
alias) and a direct Command::new(shell).arg("-c").arg(command) chain. Quote the whole chain
through its final arg call; quoting only the command text is insufficient. Unknown guards
and needs_review/abstain are supported; negative dismissal is not. Macros, attributes,
ambiguous imports, unsupported endpoint shapes and incomplete source context do not qualify.
The Rust environment profile retains up to eight native path nodes plus its primary
location, within existing byte limits; exceeding those bounds does not silently drop nodes.

Environment input need not be attacker-controlled, and command construction need not execute.
Reports remain incomplete/unverified and replay advice visibly simulated. Existing exact
report retrieval and JSON/HTML exports include the advisory history and policy identity.
HTTP launch schemas are unchanged.


## C/C++ argv-to-system advisory (Slice 104)

Use `--engine joern --joern-profile c-family-argv-system-v1` with `--language c` or
`--language cpp`. Explicit advisory policies are `joern-c-argv-review-v1` and
`joern-cpp-argv-review-v1`, respectively. The usual advisory config, key, page limits and
preconfigured run budget are required. For example, after importing a C repository:

```sh
traceproof triage-budget RUN_ID 100000 --max-requests 10
traceproof scan-run RUN_ID --engine joern --language c \
  --joern-home /path/to/joern-cli --joern-profile c-family-argv-system-v1 \
  --advisory-config /path/to/provider.json --advisory-key c-review-1 \
  --review-policy joern-c-argv-review-v1
```

For C++ substitute `cpp` and `joern-cpp-argv-review-v1`. Use `--replay` with the established
replay file format for deterministic local tests. Report retrieval/export follows the shared
report commands/API. Repeated existing attempts are skipped; use triage-attempt to continue
advice on an existing attempt, or an explicit rescan for a new attempt and possible new cost.

Only bounded global-main literal argv indexing and direct system syntax qualify. Passing
advice stays needs_review/incomplete; unsupported evidence blocks model calls. Headers are
not preprocessed, libc identity is unproven, and C++ namespace/class/template/lambda context
is unsupported. This does not certify runtime reachability or general C++ coverage.

## Public Git URL acquisition (Slice 109)

`acquire-git` prepares one source archive and CSV; it does not initialize a scan database,
scan source or invoke a model. Git must be installed. Only credential-free HTTPS on explicitly
allowed hosts is accepted. Use an immutable 40-character commit when available; full branch
or tag refs are resolved once and the resulting commit is recorded.

```sh
traceproof acquire-git https://github.com/octocat/Hello-World.git refs/heads/master \
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
scanner Job or add credentials to its manifest. Projection 13 embeds a compact provenance summary for explicitly receipt-bound intake
(Slice 112); see the persistence section below for image compatibility and binding limits.

Export reads raw blobs, preserving files marked export-ignore and bypassing checkout filters.
Symlinks, submodules and LFS pointers are rejected, as are file/path/size limits. Limits are
2,000 files, 5 MiB/file, 100 MiB source and a monitored 256 MiB temporary Git workspace.
Workspace monitoring can overshoot and is not an OS quota. Failure yields no usable CSV;
inspect acquisition.json and retry into a fresh directory after resolving the cause. Forced
termination can leave an incomplete directory; never consume it without a successful receipt.

## PVC archive batch convention

Use **archives.csv** for operator-staged local TAR/TAR.GZ/ZIP paths and reserve
**repositories.csv** for future Git-URL batches. Both CSV and archives live under the
mounted input root; source_uri is the absolute container-visible archive path. The existing
import-csv/worker workflow supports these archive batches today. See the
[PVC archive intake guide](pvc-archive-intake.md) and
[sample CSV](../examples/intake/archives.csv). Filenames do not trigger automatic dispatch.
The one-row OCP smoke demonstration accepts archives.csv or legacy input.csv as of
Slice 110, rejecting both together. Separate bounded mounted-batch execution is available through --batch-max-rows (Slice 111).

## Persisting Git acquisition provenance (Slice 112)

New acquire-git output includes acquisition_receipt and acquisition_sha256 in input.csv,
alongside the archive sha256. Admission validates and copies the receipt into durable state;
worker compares its file inventory against the captured snapshot. Keep the source archive
available until snapshotting; the receipt file is no longer needed after successful admission.

If moving to a PVC, update source_uri and acquisition_receipt to container-visible absolute
paths beneath input-root. Preserve both digest values. Archive-only archives.csv batches
need neither receipt column. Receipts are explicitly opted in, never discovered by filename.

A successful source snapshot adds acquisition_provenance.state=snapshot_bound to newly
published report projection 13, with resolved_commit and archive/receipt digests. This is
operator-supplied content binding; remote_history_authenticated remains false. Earlier
published reports stay immutable. HTML/Markdown display the commit and CSV exports add
Git commit/archive digest/binding-state columns. Existing dashboard consumers should allow
those additional columns.

An existing idempotency key returns its original admitted receipt even if the external file
has since changed. To admit a replacement, supply its updated SHA-256 and a new request key.
Digest/repository/archive mismatches reject admission; file inventory mismatch fails capture.
A failed or absent snapshot is never labeled snapshot_bound.

Slice 113 refreshes all three OCP smoke variants with this intake/report contract. Use the
recorded refreshed image digests; older immutable images still predate the receipt columns.
Do not strip receipt hashes to pretend provenance survived an older image.


## Git-URL CSV batches (Slice 114)

Use acquire-git-csv with repositories.csv and a fresh output directory. The five columns are
repo_id,url,revision,owner,classification. Supply --allowed-host explicitly; --max-rows is
1–10 and --timeout is a bounded batch acquisition deadline. Successful rows produce a
receipt-pinned archives.csv; acquisition-batch.json retains all row outcomes. Partial success
exits nonzero and never starts scans. See [Git batch guide](git-batch-intake.md) and
[sample repositories.csv](../examples/intake/repositories.csv) for staging and offline handoff.
This supersedes earlier notes that Git-URL CSV dispatch was only reserved/planned.
