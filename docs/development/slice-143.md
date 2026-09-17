# Slice 143 — Bounded npm dependency discovery

Added `dependency_discovery.py` and `get-sbom --packages`, which reads declared npm packages
from a snapshot and adds one CycloneDX `library` component each. `package-lock.json` and
`npm-shrinkwrap.json` are read from the v2/v3 `packages` map or the v1 nested `dependencies`
tree and yield `pinned` components; `package.json` yields `declared_range` components that
carry no version, only the constraint. Both records for one package stay distinct. Scoped
names are percent-encoded in the Package URL. `dev`, `optional` and `peer` declarations are
included and marked rather than dropped.

Every declaration file is re-hashed against its manifest record before parsing; digest
mismatch, unreadable, non-JSON, oversized and unrecognized-shape inputs are skipped and
counted. Workspace `link` entries are excluded as non-registry packages, and manifests under
`node_modules/` are counted as ignored installed copies rather than parsed as declarations.
Declaration-file count, per-file size and component count are bounded and refuse rather than
emit a truncated document.

Components attach to the snapshot rather than to `projection()`, revising the roadmap: a
declared dependency is a property of the captured source, not of a scan attempt, so two
attempts over one snapshot cannot disagree about it. This keeps determinism with no schema
change and no migration. Export stays opt-in; the default document is byte-identical to
Slice 142.

Fifteen new tests cover lockfile v3 and v1 shapes, scoped-name encoding, dev/optional scope marking,
workspace-link exclusion, range-versus-pinned distinctness and bom-ref uniqueness, vendored-manifest
exclusion, skip counting for unparsable and oversized inputs, coverage fields, an absent ecosystem,
opt-in determinism, the CLI flag, both bounds, and refusal when the tree is unavailable. The changed
files pass lint and formatting against an unchanged repository-wide baseline, and the full suite
passes: 1,087 tests.

**No transitive closure is resolved and no vulnerability position is established.** The
document still has no `vulnerabilities` array. A lockfile records what npm resolved when it
was written, not what is installed or deployed. npm `integrity` is recorded as a property and
never as a CycloneDX hash, because that tarball was never fetched. Only npm is parsed: an
empty inventory means no parser exists for an ecosystem, never that it is absent. SPDX output
and license inventory are not implemented.

Next: a second ecosystem parser against the same stage, then tier 3 OSV matching, which needs
a pinned vulnerability database acquired by the networked acquisition container.
