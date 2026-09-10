# Slice 38: bounded Java syntax indexing

Adds a snapshot-bound Tree-sitter Java syntax index as the next part of L0/L1.
This is syntax coverage, not resolved Java semantics or Spring qualification.

## Behavior

The Java scan runner indexes source before extraction and stops if any Java file
fails parsing or exceeds a parser limit. Standalone extraction records the index
but remains independently callable. New report projection 6 retains the syntax
coverage in language_scope and readiness. Java still remains incomplete because
semantic resolution and evidence policies are not qualified.

Indexes use the existing SourceIndex/IndexedFile tables, versioned by the parser
contract and installed parser versions. File checkpoints survive interruption;
published indexes are reused after snapshot verification. Source hashes are checked
before parsing and the snapshot is verified again before publication. No migration.

The parser records class/interface/enum/record/annotation declarations, methods,
constructors and unresolved method-invocation syntax with source lines. Comments
and strings do not become calls. This is not overload resolution, binding, taint,
reachability, framework modeling or Java compiler validation. Constructor calls,
lambda-specific scopes and inherited/member resolution are not modeled.

## Bounds and dependencies

The lockfile pins tree-sitter 0.25.2 and tree-sitter-java 0.23.5. Each file has a
1 MiB input cap and 50,000-node traversal cap. Parsing runs in an isolated Python
subprocess with a 10-second timeout and 5-second CPU limit. Linux also applies a
512 MiB address-space limit; macOS does not reliably support that limit. Production
still requires pod resource limits. Invalid UTF-8 and error-recovered syntax yield
no facts. Repository code is neither compiled nor executed by this index.

## Validation and next work

Regression tests cover real parsing, comments/string lookalikes, invalid input,
isolated execution, durable reuse, per-file failure coverage and stopping before
CodeQL on invalid Java. Real CodeQL vulnerable/fixed JDBC fixtures still yield one
and zero candidates, with syntax coverage retained and readiness incomplete.
No live model calls or bank data were used.

Next: qualify Java evidence and Spring request bindings using parser-backed facts
and real vulnerable/fixed/incomplete fixtures. Maven/Gradle remain blocked by the
initial extraction profile pending separate build qualification.
