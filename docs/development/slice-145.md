# Slice 145 — OSV matching against a pinned export

Added `osv_database.py`, `osv_matching.py`, `osv_export.py` and the `get-osv` command, plus
`get-sbom --database`, which adds a CycloneDX `vulnerabilities` array. Matching runs entirely
offline against an operator-authored export verified the way a toolchain profile is: one
`inventory_sha256` over the canonical record inventory pins the whole set, and a changed, added
or removed record is refused before any result is produced. Nothing is fetched and no database
is updated. The networked acquisition step that would produce such an export is **not** part of
this slice and remains the open half of tier 3.

Two bases produce a match: exact membership of an advisory's `versions` list, and a `SEMVER`
range evaluated under semantic-version precedence, implemented to the specification including
prerelease identifier ordering and ignored build metadata. Events are sorted before the walk so
a result never depends on how a record was written, and OSV's unbounded `"0"` lower bound is
handled explicitly. Everything else is recorded as a gap: `ECOSYSTEM` and `GIT` range types,
bounds that do not parse, and versions with no semantic-version ordering.

Maven version ordering is deliberately not implemented. `ComparableVersion` qualifier aliasing
is intricate enough that an approximation would make wrong statements about vulnerabilities, so
Maven matches on exact version lists — which GHSA-derived records generally carry — and on
`SEMVER` ranges when a record declares that ordering itself.

Each component is classified `matched`, `evaluated_no_match`, `partially_evaluated` or
`not_evaluated`, and only `evaluated_no_match` means the database was fully consulted. A
component without a resolved version is never evaluated, which is the common Maven case.
Withdrawn advisories are loaded, counted and never matched. CycloneDX analysis state is always
`in_triage`.

Twenty-four new tests cover semantic-version precedence against the specification's own ordering,
four range-bound cases, inclusive `last_affected`, an `ECOSYSTEM` range recorded as a gap rather
than a clean result, non-semver versions, a `SEMVER`-typed range evaluated for Maven, Maven
group/artifact keying, npm name-case normalization, withdrawn records, unresolved versions, profile
validation, record tampering, record addition, the `--packages` requirement, the OSV-Scanner-shaped
grouping, an empty result carrying its limitations, determinism and the CLI. The changed files pass
lint and formatting against an unchanged repository-wide baseline, and the full suite passes: 1,128
tests. No migration and no schema change.

**A match is a candidate, never a confirmed vulnerability.** It establishes no reachability, no
call path and no evidence that vulnerable code is used or deployed. Absence of a match is
meaningful only for components reported `evaluated_no_match`; an empty result never means a
repository is free of known vulnerabilities. The `results.json` shape is OSV-Scanner-*shaped*,
not an OSV-Scanner run. Database freshness is whatever the operator pinned.

Next: networked OSV database acquisition in the acquisition container, then Maven version
ordering to move Maven components out of `partially_evaluated`. Reachability, for which the
existing call index is the input, remains unimplemented and unassumed.
