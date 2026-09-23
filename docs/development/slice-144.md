# Slice 144 — Bounded Maven pom.xml dependency discovery

Added `maven_poms.py` and generalized the dependency stage across ecosystems. The npm parser
moved to `npm_manifests.py`; `dependency_discovery.py` is now an ecosystem registry that binds
declaration files to a parser, re-hashes each file against its manifest record, and merges
per-ecosystem coverage. Component identity, bounds and determinism are unchanged.

Maven never yields `pinned`. A POM has no lockfile and nearest-wins mediation can override a
stated version, so a literal version is `declared_version`. Properties declared in the same file
are substituted once and marked `version_source: properties`; `${project.version}` and
`${project.groupId}` resolve from the file's own coordinates or its `<parent>` block; a local
`<dependencyManagement>` entry supplies a version for a dependency that omits one. Everything
else stays `unresolved_version` and the component carries no version: a version inherited from a
parent POM, a property defined elsewhere, or a version managed by an imported BOM. Parent POMs
are never followed even inside the snapshot, so `inheritance_resolved` is always false. Ranges
become `declared_range`. Profile dependencies are conditional and are counted, never emitted.
Poms under `target/` are build output and counted as ignored.

Any `<!DOCTYPE` or `<!ENTITY` declaration is refused before parsing and counted. This was
verified rather than assumed: `xml.etree.ElementTree` expands internal entities, so an
attacker-supplied DTD would be a billion-laughs sink inside the scanner. A real `pom.xml` needs
no DTD, so refusal costs nothing.

Renamed in the CycloneDX output as the stage stopped being npm-only: `veriflow:npm_scopes` to
`veriflow:declared_scopes`, `veriflow:vendored_manifests_ignored` to
`veriflow:excluded_declarations_ignored`, and `veriflow:dependency_pinned_components` to
`veriflow:dependency_resolution_counts`. Skip reasons and parsed-file counts are now keyed by
ecosystem. `veriflow:npm_integrity` stays npm-specific.

Seventeen new tests cover literal, interpolated, managed, ranged and unresolvable versions,
`${project.version}` from a parent block, imported-BOM and profile gap counting, optional and test
scopes, namespaceless poms, malformed and foreign XML, build-output exclusion, three entity
declaration shapes, a billion-laughs document refused before parsing, ecosystem coexistence and
determinism. The six npm tests asserting renamed properties were updated. The changed files pass
lint and formatting against an unchanged repository-wide baseline, and the full suite passes: 1,104
tests. No migration and no schema change.

**No transitive closure, no POM inheritance and no vulnerability position are established.** The
document still has no `vulnerabilities` array. Only npm and Maven are parsed: an empty inventory
means no parser exists for an ecosystem, never that it is absent. A `declared_version` is what a
file stated, not what a build would resolve. SPDX output and license inventory are not
implemented.

Next: tier 3 OSV matching, which needs a pinned vulnerability database acquired by the networked
acquisition container, or a further ecosystem parser against the same stage.
