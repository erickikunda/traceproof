# Slice 44: opt-in automatic single-language selection

Adds `--language auto` to codeql-extract, scan-run and scan-import using the captured,
verified snapshot inventory. Exactly one detected source language must be present and
supported (currently Python or Java). Mixed source languages, unsupported languages,
and snapshots with no recognized source language fail selection with detected names.
No language is chosen merely because it has the most files.

Non-source files such as README and POM do not create language ambiguity. Recognition
is extension-based, not semantic classification or content sniffing. Unknown extensions
are not recognized language coverage; generated/vendor/test distinctions remain pending.
Explicit language selection remains available for partial scans, with other detected
languages disclosed as before. The default remains Python for compatibility.

Selection does not choose queries, fan out to multiple analyzers, combine reports or
execute repository builds. The operator still supplies the correct query. scan-import
uses one query for its page: do not treat auto as per-language query routing. Java
profile selection remains explicit; use --java-profile source-only when needed for
build-layout repositories. An incompatible profile fails rather than silently changing.

The resolved language drives the existing profile-specific skip checks. Extraction
scope records language_selection (automatic or explicit); reports retain that scope.
Runner responses also record requested_language alongside resolved language. Existing
immutable reports remain unchanged. No migration or live model calls.

## Usage

```sh
traceproof scan-run RUN_ID QUERY_PATH --language auto
traceproof scan-run JAVA_RUN_ID JAVA_QUERY_PATH --language auto --java-profile source-only
```

The repeatable Spring script accepts --auto-language for real CodeQL qualification.
Tests cover Python/Java selection, unsupported/mixed/empty inventories, auto-selected
attempt reuse, Java-only copying and persisted selection metadata. 401 regression tests
passed. Mixed-language dispatch and consolidated reporting remain future work; this
is only the first selection step in the planned automation path.

Next: continue the prioritized language track, including C#/ASP.NET while isolated
Spring build execution and dependency access are being qualified. Do not replace
language coverage delivery with further CLI conveniences.

Real CodeQL validation completed: all four Maven-layout Spring cases passed with
automatic language selection, including retained report selection metadata.
