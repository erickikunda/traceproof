# Slice 40: real Spring-style SQL path acceptance

Adds a reproducible source-only Spring-style controller acceptance suite, using the
installed official CodeQL Java SQL-injection path query. This advances L1 evidence
qualification beyond annotation inventory. It does not qualify a built Spring application.

## Fixture matrix

| Fixture | Expected behavior |
|---|---|
| Vulnerable | One java/sql-injection candidate with retained request-parameter-to-JDBC path |
| Fixed | Zero candidates after JDBC prepared-statement parameterization |
| Lookalike | Zero candidates when the same annotation names come from a foreign namespace |
| Incomplete | Java syntax failure stops before extraction and publication |

The controller uses explicit GetMapping, RequestParam and RestController imports.
The acceptance runner verifies candidate counts, exact report retrieval, Java syntax
coverage, three annotation observations, and the namespace hints. It materializes the
vulnerable evidence bundle and checks a complete retained flow with the expected
source and sink lines in the same thread. All successful scan reports must retain
incomplete readiness, and all cases must make zero model calls.

## Reproduce

```sh
uv sync
uv run python scripts/validate_spring.py /path/to/java-queries/Security/CWE/CWE-089/SqlTainted.ql work/spring-acceptance
```

Use a new output directory. The runner writes isolated SQLite state, synthetic archives,
JSON/HTML reports, a source-containing vulnerable-bundle.json, and validation.json.
A failed assertion exits nonzero. The Java and Spring scripts share intake/scan/report
orchestration to avoid divergent validation logic. The original validate_java.py
interface and JDBC concatenation fixtures remain available.

## Qualification boundary

The installed CodeQL 2.27.0 / java-queries 1.11.10 query declares java/sql-injection,
path-problem and high precision. This is tool metadata, not a measured precision claim.
Unlike the earlier concatenation query, this checks a retained modeled data-flow path.

No Spring jars are supplied and no Maven/Gradle build is executed. The existing
java-dependency-free-v1 profile name means this run supplies source without build or
dependency artifacts; it does not mean that Spring source has no external imports.
CodeQL's modeled source-only result does not prove runtime dependency resolution,
controller registration, deployed endpoint reachability or exploitability. No stub
Spring classes are introduced to manufacture a result. Maven/Gradle, WebFlux, runtime
bindings, Java LLM evidence policies and broad Spring support remain unqualified.
These synthetic cases do not establish bank-corpus recall or false-positive rates.

No runtime/schema migration or provider configuration changes. No bank data or live
model calls. Next: Java SQL evidence-policy qualification against these pinned source
and sink paths, followed by separately qualified Spring build profiles.

Validation completed: all four real acceptance cases passed; 386 regression tests
passed, with lint, formatting and package build checks passing.
