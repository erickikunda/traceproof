# Slice 149 — Bounded go.mod dependency discovery

Added `go_modules.py`, registering Go as the third ecosystem in the dependency stage, with OSV
matching and import evidence wired through. `go.sum` is deliberately not read as a component
source: it covers the whole module graph rather than what a build resolves, so treating it as an
inventory would over-report.

`replace` is the load-bearing directive. It changes what a build actually resolves, so a replaced
requirement is emitted with **no version** and the resolution `replaced`, which makes it
unmatchable, while a module-path replacement target is emitted as its own component. This is a
correctness requirement, not a presentation choice: if a replacement is a patched fork, matching
the original's declared version would report a vulnerability the build does not have. A
version-specific replace applies only to the version it names, a local replacement yields no
registry component, and `exclude` directives are counted rather than emitted.

`// indirect` requirements are marked rather than dropped, so Go surfaces transitive modules that
npm manifests and Maven POMs do not. That is not closure resolution — the Go tool recorded those
entries and VeriFlow only read them — so `transitive_resolved` stays false.

Go versions carry a `v` prefix while OSV Go records use plain semantic versions. Ordering strips
the prefix and exact version lists are tried in both forms, so `v1.9.1` matches a record written
as `1.9.1`. Pseudo-versions and `+incompatible` versions parse as semantic versions and order
correctly.

Import evidence for Go is exact rather than conventional: an import path is the module path or a
package below it, guaranteed by the Go toolchain. `github.com/gin-gonic/gin/binding` matches its
module and `github.com/a/bc` does not match `github.com/a/b`, which is asserted by test. A Go
`not_observed` is stronger than a Maven one and still not evidence of non-use.

Twenty-five new tests cover block and single-line requirements, indirect marking, global, version-
specific, local and block-form replacements, excluded versions, pseudo and qualified versions, four
malformed requirement shapes, comment handling, vendored exclusion, exact and boundary-respecting
import evidence, determinism, module-path keying, both version-list forms, three range bounds and
the replaced-module invariant. The changed files pass lint and formatting against an unchanged
repository-wide baseline, and the full suite passes: 1,245 tests. No migration and no schema change.

**Go is the prerequisite for symbol-level reachability, not reachability itself.** The Go
vulnerability database publishes `ecosystem_specific.imports` with affected symbols, which is why
this ecosystem was chosen next, but symbol matching is **not implemented** and
`vulnerable_symbol_matching` remains `none`. No call graph is resolved. A `go.sum` present in a
repository is ignored, so module hashes are not recorded.

Next: OSV acquisition container qualification, which is still outstanding, then Go symbol matching
as the first ecosystem where reachability could move past import evidence.
