# Slice 150 — Go package and symbol evidence

Added `go_symbols.py`, which reads the `ecosystem_specific.imports` data that the Go vulnerability
database publishes — vulnerable package path and affected symbols — and classifies each Go match
against first-party source. No other parsed ecosystem provides this data.

Each Go match becomes `symbol_referenced`, `package_imported`, `package_not_imported`,
`no_symbol_data` or `not_evaluated`. `symbol_referenced` records which symbols were found. This
is finer than Slice 148's module-level import evidence: it distinguishes a module that is used
from the specific vulnerable package being imported, and from one of the named symbols actually
appearing.

**`package_not_imported` is the strongest negative this pipeline produces and is still not a
safety conclusion.** An imported package can call the vulnerable one internally, a transitive
dependency can import it, and generated or build-tagged code may be absent from the snapshot. The
CycloneDX analysis state stays `in_triage` for every state, which is asserted by test for the
`package_not_imported` case specifically.

The scan resolves the identifier an import binds — exactly when aliased, and by convention
otherwise, since a package's declared name need not match the last element of its path. Major
version suffixes (`/v2`) and `gopkg.in` style suffixes (`.v3`) are handled. A method symbol such
as `Decoder.Decode` is searched by its receiver type because a call site cannot be resolved
lexically, so `package_imported` versus `symbol_referenced` is a priority signal, not proof of
use. Blank imports bind no name. Dot imports put symbols in scope unqualified and are counted as
unresolvable rather than guessed at. Platform constraints are recorded and never applied, because
the build target is unknown.

Twenty new tests cover five identifier conventions, alias and blank and dot import binding,
referenced and unreferenced symbols, method symbols by receiver, an unimported vulnerable package,
advisories without symbol data, absent Go source, identifier-boundary respect so `gin.ParseAll` does
not match `Parse`, platform constraints recorded but unapplied, non-Go ecosystems receiving no
symbol evidence, the OSV export shape and determinism. The changed files pass lint and formatting
against an unchanged repository-wide baseline, and the full suite passes: 1,265 tests. No migration
and no schema change.

**This is reference evidence, not reachability.** No call graph is resolved and third-party code
remains absent from the snapshot, so nothing establishes that vulnerable code executes.
`govulncheck` answers that question by building the whole program including dependencies;
VeriFlow has neither the dependencies nor the build. Only Go advisories carry symbol data, so
npm and Maven matches are unaffected by this slice.

Next: OSV acquisition container qualification, which remains the outstanding item from Slice 147.
