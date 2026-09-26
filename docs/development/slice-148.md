# Slice 148 — Import evidence for declared dependencies

Added `dependency_usage.py` and the `--usage` option on `get-sbom` and `get-osv`. A bounded
lexical scan of first-party source records whether each declared package is named by an import,
producing `import_observed`, `not_observed` or `not_evaluated` per component.

**This is import evidence and is not reachability analysis, which the inputs do not support.**
Reachability would establish that a vulnerable function is invoked. The OSV schema has no standard
field naming affected functions, and npm and Maven records — the two parsed ecosystems — carry
version ranges only, so there is usually no symbol to be reachable to. Third-party code is also
absent from the snapshot: `node_modules/` is excluded from declarations by design and JARs are
never present, so no call path can cross from first-party source into a dependency. The index's
own `static_candidate` is already documented as never proving reachability.

The asymmetry between the states is the design. `import_observed` is positive evidence that raises
priority. `not_observed` establishes nothing: transitive use, dynamic `require`, reflection,
framework wiring, service loaders and configuration-driven instantiation all leave no import in
first-party source. A vulnerability's CycloneDX `analysis.state` stays `in_triage` whatever the
usage state, which is asserted by test for both observed and unobserved cases.

Detection is lexical rather than parsed and says so in `veriflow:usage_detection_method`, so a
specifier inside a comment or string can be reported. Over-reporting is the conservative
direction: it says investigate, where under-reporting would say clear. Installed and build
directories are excluded as not first-party, and minified or bundled JavaScript is excluded
because a bundle inlines its dependencies and would report every one as imported. Skipped files
are counted, because a skipped file may hold the import that would have changed a `not_observed`.

Maven carries a second approximation: an import is matched against the dependency's groupId
prefix, which is a convention rather than a rule. `junit:junit` publishes `org.junit`, so a
project using JUnit reports `not_observed`; that counter-example is a fixture, not a footnote.

Twenty-seven new tests cover specifier reduction, six import forms, observed and unobserved
components, absent-language and skipped-file handling, vendored and bundled exclusion, the Maven
convention with its junit counter-example, static and wildcard Java imports, the `--packages`
requirement and determinism. Two further tests assert the analysis state never moves and that the
OSV export carries usage with its limits. The changed files pass lint and formatting against an
unchanged repository-wide baseline, and the full suite passes: 1,220 tests. No migration and no
schema change.

**Genuine reachability remains unimplemented and unassumed.** It would need a per-ecosystem
vulnerable-symbol source and third-party code in scope; neither exists in this pipeline. No call
graph is resolved and no symbol is matched. Only npm and Maven are scanned, so a component in any
other ecosystem is `not_evaluated` rather than unused.

Next: OSV acquisition container qualification, which is still outstanding, and a per-ecosystem
symbol source if reachability is ever to be more than import evidence.
