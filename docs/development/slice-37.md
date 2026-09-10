# Slice 37: language foundation and first Java static scan

This starts L0/M3.1a and L1/M3.1b. Python remains the default; the full Java/Spring
acceptance milestone is not complete. No migration is required beyond schema 0009.

## Delivered behavior

- `--language java` on extraction, scan-run and scan-import selects the new
  dependency-free Java profile. Analysis inherits the extraction language.
- A shared adapter registry and snapshot inventory distinguish detected languages
  from supported analysis. Extensions cover the requested languages plus Kotlin.
- Each invocation analyzes one selected language. Reports disclose other detected
  languages; these prevent a whole-snapshot static review-ready result.
- New report projection 5 carries language and scope through JSON, HTML, Markdown
  and CSV. Existing materialized reports remain unchanged. Exact retrieval works.
- Batch skip-existing decisions are language-specific. Comparisons explicitly flag
  differing languages as incompatible. Benchmark language expansion remains pending.

## Java boundary

The initial profile uses CodeQL build mode `none` with dependency-free Java source.
Maven, Gradle and Ant descriptors, build wrappers, JARs and Kotlin files are rejected
at preflight. This does not qualify external dependencies, generated code or Spring.
The pipeline bypasses Python AST indexing for Java. Java semantic indexing and LLM
evidence policies are not implemented, so readiness remains incomplete with
`java_semantic_index_not_qualified`. No automatic vulnerability confirmation or
suppression is introduced. A rejected preflight does not create an extraction report.

## Validation

The regression suite passes: **374 tests**. New tests cover language inventory,
unsupported adapters/project inputs, readiness, exact report retrieval, CSV scope
and language-specific skip decisions.

`scripts/validate_java.py QUERY_PATH NEW_OUTPUT_DIRECTORY` provides repeatable real
CodeQL acceptance with isolated SQLite state and synthetic archives. CodeQL 2.27.0
and bundled java-queries 1.11.10 produced one candidate for JDBC string concatenation
and zero for the prepared-statement counterpart. Both analyses completed and both
reports correctly remained incomplete. No model calls were made.

The query `java/concatenated-sql-query` is medium precision and produces a problem
result, not a source-to-sink path. This is a static candidate demonstration, not
verified remote exploitability, Spring qualification or corpus recall measurement.

## Next

Continue Java semantic indexing/evidence qualification and real Spring fixtures,
with Maven and Gradle profiles qualified separately, before moving to C#/ASP.NET.
