# SBOM and OSV export roadmap — Slice 142

Assessed against the current repository after Slice 141. The question is where component
inventory (SBOM) and known-vulnerability (OSV) output belong relative to the existing
report and SARIF surfaces. The assessment concludes they are not peer output formats of
SARIF and cannot be added as one. Slice 142 implements tier 1; Slices 143 and 144 implement the
npm, Maven and Go parsers of tier 2; Slices 145-147 implement tier 3 — matching with semantic-version
and Maven orderings, and networked acquisition of the pinned export. Slice 148 adds import
evidence, which is **not** reachability; the distinction is set out below.

## Current output surface

| Surface | Module | Shape | Derived from |
|---|---|---|---|
| Published report | `reports.py` | JSON / Markdown / HTML / scan-csv / candidates-csv | content-addressed `projection()` body |
| SARIF inward | `sarif.py` | normalization to candidates | scanner output bytes |
| SARIF outward | `sarif_export.py` | exact original bytes, integrity-checked | scanner output bytes |
| Comparison / scorecards | `comparison.py`, `scorecard*.py` | JSON / Markdown / HTML | published reports |

SARIF is not a rendered format. `render_report` never emits it, and `get_sarif` returns the
scanner's own bytes after a recorded SHA-256 check. There is therefore no existing "output
format" seam that a new SBOM encoder can simply join.

## Why SBOM and OSV are not peers of SARIF here

**No package inventory exists.** No module parses `package.json`, `pom.xml`, `go.mod`,
`Cargo.toml`, `*.csproj` or any lockfile belonging to a scanned repository.
`java_dependencies.py` and `csharp_dependencies.py` are pinned *operator-supplied build
toolchain* profiles for CodeQL extraction — SDK references and Maven artifacts used to run
the analyzer. They describe VeriFlow's analysis environment, not the target's dependencies.

**The only inventory available today is file-level.** `SnapshotManifest.files` records
`path`, `size_bytes` and `sha256` per extracted file (`artifacts.py`), verified end to end by
`ArtifactStore.verify`. That is a file inventory, not a component inventory.

**An OSV record is a verdict.** OSV describes a known vulnerability affecting a package
version range, keyed by ecosystem and package. VeriFlow candidates are unproven
first-party source observations carrying CWE scope and no CVE identity. Encoding candidates
as OSV records would assert precisely the conclusion every gate in this codebase withholds.
OSV becomes meaningful only as *matching a package inventory against a vulnerability
database*, which is a new pipeline stage requiring network access.

**The container SBOM is a different artifact.** `docs/plans/implementation-plan.md` and
`docs/architecture/system-design.md` reference an SBOM for VeriFlow's own pinned images.
That is supply-chain evidence for the scanner, unrelated to the scanned repository. Keep the
two namespaces distinct in operator documentation.

## Tiers

| Tier | Output | New analysis required | Network | Status |
|---|---|---|---|---|
| 1 | CycloneDX file inventory for a snapshot | none | no | Slice 142 |
| 2 | CycloneDX package inventory | dependency discovery stage | no | npm in Slice 143, Maven in Slice 144, Go in Slice 149; other ecosystems queued |
| 3 | OSV matching and OSV-Scanner-shaped results | tier 2 plus pinned vulnerability database | acquisition container only | matching in Slices 145-146, acquisition in Slice 147, container qualified in Slice 151 |

Each tier is independently useful and must not be collapsed. Tier 1 makes no claim that the
tier 2 inventory exists; an operator reading a tier 1 document must not mistake it for a
dependency bill of materials.

### Tier 1 — file inventory (Slice 142)

`sbom_export.py` re-encodes the recorded snapshot manifest as CycloneDX 1.6 with
`component.type: file`, one component per manifest record carrying its SHA-256. It follows its
sibling `sarif_export.py` in shape: repository ownership check, bounded
output, no filesystem path taken from stored tool output.

It is deliberately **not** added to `render_report`. The published report body is capped at
8 MiB (`MAX_REPORT_BYTES`) and is a summary projection; a 20,000-file inventory does not
belong inside it, and the report is keyed to a run and attempt rather than a snapshot.

Determinism is a requirement, not a convenience. The document omits `metadata.timestamp` and
derives `serialNumber` from the snapshot identity, so an identical snapshot yields identical
bytes — the same property `publish_report` enforces for reports. The `vulnerabilities` array
is absent by construction.

### Tier 2 — package inventory

The repeatable shape, following the Joern profile convention:

- `src/veriflow/dependency_discovery.py` — bounded per-ecosystem parsers over snapshot
  files emitting Package URLs. Manifest and lockfile inputs are untrusted repository content
  and must be parsed under the same discipline as source: explicit size bounds, no entity
  resolution for XML (`pom.xml`, `*.csproj`), no evaluation of build scripts.
- Declared dependencies are **candidate components**. Without executing a build and without
  network resolution the transitive closure is unavailable; a lockfile yields pinned
  versions while a bare manifest yields ranges, and an unpinned range is not a component
  identity. Record which was observed per component.
- A `dependency_coverage` block sibling to `discovery_coverage` carries ecosystems seen,
  files parsed, files skipped and `transitive_resolved: false`.
- Components attach to the **snapshot**, not to `projection()`. This revises the original
  plan: a declared dependency is a property of the source a snapshot captured, not of a scan
  attempt, and two attempts over one snapshot cannot disagree about it. Keying the inventory
  to the snapshot keeps determinism without a schema change, and `get-sbom --packages` reads
  the verified tree directly. Report-side integration remains available later if an operator
  needs dependencies inside a published report, and would then be a projection of this stage
  rather than its home.
- Bound the declaration-file count, per-file size and component count, and refuse rather than
  emit a truncated document on overflow.
- Fixtures per ecosystem asserting exact component counts, plus pinned/unpinned negatives.

SPDX output is not implemented. Adding it is an encoder over the same discovery result and
should not change the stage.

**Resolution vocabulary.** `pinned` is reserved for a version a lockfile resolved. `declared_version`
is a version a declaration states without a lockfile behind it. `declared_range` is a constraint,
carrying no component version. `unresolved_version` is a dependency whose version the snapshot
does not establish at all. An ecosystem without a lockfile can never produce `pinned`.

**npm (Slice 143).** `package-lock.json` and `npm-shrinkwrap.json` supply pinned versions from
the v2/v3 `packages` map or the v1 nested `dependencies` tree; `package.json` supplies ranges,
which are recorded as `declared_range` with no component version. Workspace `link` entries are
not registry packages and are excluded. Manifests under `node_modules/` are installed copies,
not declarations, and are counted as ignored rather than parsed. npm `integrity` is the
registry tarball digest — it is recorded as a property, never as a CycloneDX `hashes` entry,
because VeriFlow never saw that tarball.

### Tier 3 — OSV matching

Scanning runs offline by contract, so a vulnerability database cannot be fetched during a
scan. The consistent placement is the existing networked Git/GCS acquisition container:
acquire a pinned, digest-recorded OSV database export as a versioned artifact, hand it across
the shared mount, and match offline against the tier 2 inventory.

Matches remain candidates. Version-range matching is approximate, an advisory range is not a
statement about the deployed artifact, and no match says anything about reachability. The
call-graph data already in the index is the natural later refinement and must not be assumed
by the initial matcher. Output is an OSV-Scanner-shaped `results.json` encoder once matching
exists; the encoder is the small part.

**Acquisition and matching are separate containers.** The database is a pinned export verified the
way `csharp_dependencies.py` verifies a toolchain profile: one `inventory_sha256` over the
canonical record inventory pins the whole set, and a changed, added or removed record is refused.
Matching never touches the network.

Slice 147 adds `acquire-osv`, which produces such an export, following the GCS contract's split:
`osv_acquisition.py` holds the gates against an `ExportReader` protocol, and `osv_reader.py` is
the only networked component. Redirects are refused outright, because a redirect could leave the
validated host. An unexpected archive member aborts the acquisition rather than being skipped — a
silently incomplete database would later be reported as fully evaluated, which is the failure
this stage exists to prevent.

**Freshness cannot be pinned the way a commit can.** Git acquisition pins a revision and GCS pins
a generation; the OSV export has no stable published digest and changes continuously. Acquisition
therefore accepts an operator-supplied per-ecosystem digest (`operator_pinned`) or, with an
explicit opt-in, records the digest it observed (`observed_only`). The resulting export is
internally pinned either way, so matching stays deterministic; what differs is whether the input
was approved in advance. The receipt states which applied.

**What is evaluated, and what is refused.** Three bases produce a match: exact membership of an
`affected.versions` list, a `SEMVER`-typed range under semantic-version precedence, and — since
Slice 146 — an `ECOSYSTEM`-typed range on a Maven package under Maven's `ComparableVersion`
ordering. An ordering is bound to a range type and an ecosystem; it is never inferred from how a
version string happens to look. Everything else is recorded as a gap rather than resolved:
`ECOSYSTEM` ranges on ecosystems with no implemented ordering, `GIT` ranges, and versions that
the required ordering cannot parse.

Slice 145 deliberately withheld Maven ordering on the grounds that an approximation of
`ComparableVersion` would make wrong statements about vulnerabilities. Slice 146 does not relax
that standard; it meets it. The implementation is a faithful port of the algorithm — qualifier
aliasing, single-letter shorthand, trailing-padding normalization and the integer/qualifier/list
rank rules — validated against the ordering and equivalence vectors from Maven's own
`ComparableVersionTest`. Approximation was the objection, not ordering itself.

**A component is never silently clean.** Each is classified `matched`, `evaluated_no_match`,
`partially_evaluated` (something about it could not be evaluated) or `not_evaluated` (no resolved
version, or an ecosystem the database does not cover). Only `evaluated_no_match` means the
database was fully consulted. A component with an unresolved version — the common Maven case —
is never evaluated at all, so an empty result over an inheritance-heavy repository says almost
nothing. Withdrawn advisories are loaded, counted and never matched.

Slice 151 qualified the acquisition container against the live export on linux/arm64. Unit tests
still drive a fake reader and never open a socket; the real fetch is exercised only by
`scripts/validate_osv_acquisition.py`, which drives the pinned image from the host. Qualification
corrected three limits that were an order of magnitude too low for the real export, and measured
a per-run load cost of roughly 50 seconds and 1.7 GiB for a three-ecosystem database. Slice 153 adds an amd64
build and qualification under emulation, with a byte-identical pinned inventory across both
architectures; native amd64 execution, OCP and registry acceptance remain outstanding.

Slice 152 makes that cost optional with `--cache`, which reuses a derived index keyed by the
profile digest and cuts a three-ecosystem run from 52.8 to 10.5 seconds. The saving is precisely
the integrity check: a cache hit does not re-read the records, so a record modified after the
cache was written is not detected, where the uncached path refuses that database outright. The
tradeoff is therefore opt-in, named per document in `database_verification` as `reverified` or
`cached`, and pinned by a test that asserts the undetected case rather than leaving it implicit.

## Reachability, and why Slice 148 does not claim it

Reachability analysis would establish that a vulnerable function is actually invoked. VeriFlow
cannot establish that for a declared dependency, for two reasons that are properties of the
inputs rather than of the implementation:

- **The vulnerable symbol is usually unknown.** The OSV schema has no standard field naming
  affected functions. Go's vulnerability database publishes `ecosystem_specific.imports` with
  symbols, and Slice 149 adds the Go parser those records need — but the symbol matching is not
  implemented, and npm and Maven records generally carry version ranges only. Without a symbol
  there is nothing to be reachable *to*.
- **Third-party code is not in the snapshot.** `node_modules/` is excluded from declarations by
  design and JARs are never present, so no call graph can cross from first-party source into the
  dependency. The index's own `static_candidate` is documented as never proving reachability even
  within first-party code.

Slice 149 added the Go parser and Slice 150 uses the symbol data that Go's database does carry,
which narrows the first gap for one ecosystem but not the second: third-party code is still
absent, so nothing resolves a call path. Go symbol evidence is therefore *reference* evidence,
not reachability, and it is described under its own heading below.

Slice 148 implements what the inputs support everywhere else: **import evidence**. A lexical scan of
first-party source records whether a declared package is named by an import or require. The
states are `import_observed`, `not_observed` and `not_evaluated`, and the asymmetry is the whole
point:

- `import_observed` is **positive** evidence that the dependency is used, and raises priority.
- `not_observed` is **not** evidence of non-use. Transitive use, dynamic `require`, reflection,
  framework wiring, service loaders, resource loading and configuration-driven instantiation all
  leave no import in first-party source. It never clears a candidate.
- `not_evaluated` means no source of that language was read at all.

The CycloneDX analysis state stays `in_triage` whatever the usage state, and this is asserted by
test. Usage prioritizes; it never adjudicates. Detection is lexical rather than parsed, so it can
over-report a specifier appearing in a comment or string — the conservative direction, because
over-reporting says *investigate* while under-reporting would say *clear*. Maven adds a second
approximation: matching an import against a groupId prefix is a convention, not a rule, and
`junit:junit` publishing `org.junit` is the standing counter-example carried in the fixtures.

### Go symbol evidence (Slice 150)

The Go vulnerability database publishes `ecosystem_specific.imports` with the vulnerable package
path and affected symbols, which no other parsed ecosystem provides. Slice 150 reads it and
classifies each Go match:

- `symbol_referenced` — first-party source imports the vulnerable package and names one of the
  advisory's symbols in a qualified reference.
- `package_imported` — the vulnerable package is imported but no named symbol was referenced.
- `package_not_imported` — the module is used but that specific package path is not imported.
- `no_symbol_data` — the advisory carries no import data.
- `not_evaluated` — no Go source was read.

`package_not_imported` is the strongest negative this pipeline can produce, and it is still **not
a safety conclusion**. An imported package can call the vulnerable one internally, a transitive
dependency can import it, and generated or build-tagged code may not be present. The analysis
state stays `in_triage` for every one of these states, asserted by test.

The scan is lexical. It resolves the identifier an import binds — exactly when aliased,
conventionally otherwise, since a package's declared name need not match its path — and searches
for `identifier.Symbol`. A method symbol such as `Decoder.Decode` is searched by its receiver
type, because a call site cannot be resolved lexically. Blank imports bind no name; dot imports
put symbols in scope unqualified and are counted as unresolvable rather than guessed at. Platform
constraints (`goos`/`goarch`) are recorded and never applied, because the build target is unknown.

Genuine reachability remains open: it would need third-party code in scope and a resolved call
graph, which is what `govulncheck` does by building the whole program. Neither is assumed
anywhere in this pipeline, and `call_graph_resolved` is false throughout.

**Maven (Slice 144).** `pom.xml` supplies `declared_version` — never `pinned`, because Maven has
no lockfile and nearest-wins mediation can override a stated version. Properties declared in the
same file are substituted once and marked `version_source: properties`; `${project.version}` and
`${project.groupId}` resolve from the file's own coordinates or its `<parent>` block. A
`dependencyManagement` entry in the same file supplies a version for a dependency that omits one,
marked `dependency_management`. Everything else stays `unresolved_version`: a version inherited
from a parent POM that is not read, a property defined elsewhere, or a version managed by an
imported BOM. Parent POMs are never followed, even within the snapshot, so `inheritance_resolved`
is always false. Profile dependencies are conditional and are counted, never emitted. Poms under
`target/` are build output, not declarations.

A `pom.xml` needs no DTD, so any `<!DOCTYPE` or `<!ENTITY` declaration is refused before parsing
and counted as `maven:doctype_refused`. This is not incidental: `xml.etree.ElementTree` expands
internal entities, so parsing an attacker-supplied DTD would be a billion-laughs sink inside the
scanner. Refusing the document is the conservative reading and costs nothing a real POM needs.

**Go (Slice 149).** `go.mod` supplies `declared_version`; Go has no lockfile in the npm sense, and
`go.sum` is deliberately **not** read as a component source — it covers the whole module graph
rather than the build, so treating it as an inventory would over-report.

The load-bearing detail is `replace`. A replace directive changes what a build actually resolves,
so reporting the replaced module at its required version would be a false statement about the
build — and if the replacement is a patched version, matching the original against advisories
would be actively wrong. A replaced requirement is therefore emitted with **no version** and the
resolution `replaced`, which makes it unmatchable, while a module-path replacement target is
emitted as its own component. A version-specific replace applies only to that version. A local
replacement (`=> ./path`) yields no registry component at all. `exclude` directives are counted,
never emitted.

`// indirect` requirements are marked rather than dropped, so Go shows transitive modules that
npm manifests and Maven POMs do not. This is still not closure resolution: the Go tool recorded
those entries, VeriFlow only read them, and `transitive_resolved` stays false.

Go versions carry a `v` prefix while OSV Go records are written as plain semantic versions, so
ordering strips the prefix and exact version lists are tried in both forms.

Go is also the ecosystem where symbol-level reachability first becomes possible, because the Go
vulnerability database publishes `ecosystem_specific.imports` with affected symbols. Slice 150 implements that
reading as *reference* evidence; it still resolves no call graph.

## CycloneDX analysis state

If source candidates are ever carried in a CycloneDX `vulnerabilities` array, the only
honest `analysis.state` is `in_triage`. A failed evidence gate is an abstention and must
never become `not_affected` or `false_positive`, and no discovery result may be recorded as
`exploitable`. Tier 1 avoids the question by omitting the array entirely.

## Non-claims

Tier 1 is a re-encoding of recorded intake evidence. It establishes no dependency inventory,
no license inventory, no package identity and no vulnerability position. A complete SBOM in
the sense required by supply-chain attestation is not delivered by any tier here, and none of
these tiers produce a signed attestation. Zero components of a given ecosystem never means
that ecosystem is absent; it means no parser has been written for it.

Evidence: `src/veriflow/sbom_export.py`, `src/veriflow/osv_database.py`,
`src/veriflow/go_modules.py`, `src/veriflow/go_symbols.py`,
`src/veriflow/dependency_usage.py`,
`src/veriflow/osv_acquisition.py`, `src/veriflow/osv_reader.py`,
`src/veriflow/maven_version.py`,
`src/veriflow/osv_matching.py`, `src/veriflow/osv_export.py`,
`src/veriflow/dependency_discovery.py`,
`src/veriflow/npm_manifests.py`, `src/veriflow/maven_poms.py`, `src/veriflow/artifacts.py`
manifest capture and verification, and `tests/test_sbom_export.py`,
`tests/test_dependency_discovery.py`, `tests/test_maven_dependencies.py`,
`tests/test_osv_matching.py`, `tests/test_maven_version.py`,
`tests/test_osv_acquisition.py`, `tests/test_dependency_usage.py`,
`tests/test_go_modules.py`, `tests/test_go_symbols.py`.
