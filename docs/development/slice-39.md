# Slice 39: Spring annotation evidence inventory

Adds parser-backed annotation facts to Java syntax indexing. This is an initial
framework evidence inventory, not qualified Spring vulnerability detection.

## Delivered behavior

Java parser version 2 retains annotation names, source lines, enclosing scope and
method/parameter/declaration targets. Explicit imports and fully qualified syntax
produce name hints; wildcard imports and absent/ambiguous imports stay unresolved.
Comments and strings cannot manufacture annotation facts. The index report includes
an annotation count and up to 200 Spring-name observations with file hashes, total
count and a truncation flag. Full per-file parser facts remain in index checkpoints.
Extraction and published JSON reports already carry this index through language_scope.

The initial vocabulary covers RequestMapping, HTTP mapping variants, RestController,
and common explicit request-parameter/body/header/path annotations. Foreign imports
and unqualified lookalikes remain visible with spring_namespace_hint false. Even an
explicit Spring namespace hint does not prove identity: local shadowing, dependencies,
meta-annotations and runtime configuration are unresolved. All observations explicitly
retain binding_proven=false and request_binding_proven=false. Annotation arguments
and source values are not included in this projection.

No Java evidence policy is enabled for LLM triage. Java readiness remains incomplete.
No Maven/Gradle profile, controller execution, endpoint reachability, guard effectiveness,
WebFlux/MVC distinction or interprocedural flow is claimed. Build descriptors are still
rejected by the current extraction profile. Indexing itself needs no Spring dependency
and does not compile or execute source. Existing immutable reports/indexes are preserved;
parser version 2 creates a fresh index. No database migration is required.

## Validation

Tests exercise imported and qualified annotations, method and parameter targets,
comments/string lookalikes, foreign/wildcard imports, local annotation definitions,
bounded output with truncation and snapshot-bound persistence. Existing Java syntax
and Python tests remain applicable. No model calls or bank data were used.

## Next

Connect qualified Java source/sink evidence to retained CodeQL paths and add real Spring
vulnerable/fixed/incomplete extraction fixtures. Qualify Maven and Gradle separately.
This slice advances L1 but does not complete it or add benchmark completion credit.

## References

The vocabulary follows Spring's [request mapping documentation](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-requestmapping.html)
and [RequestBody documentation](https://docs.spring.io/spring/reference/7.1/web/webmvc/mvc-controller/ann-methods/requestbody.html).
These describe framework behavior; this implementation records syntax only.
