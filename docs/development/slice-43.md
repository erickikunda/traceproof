# Slice 43: explicit Java source-only profile for build-layout repositories

Adds `--java-profile source-only` to codeql-extract, scan-run and scan-import, together
with `--language java`. The default dependency-free profile retains its existing
rejections. Source-only accepts repositories containing Maven/Gradle descriptors,
wrappers, JARs and Kotlin, but extracts only Java source from a verified attempt-local
copy. It does not qualify Maven or Gradle builds.

## Input boundary and provenance

The copy preserves each Java snapshot-relative path and byte content. Hashes are checked
after copying and after extraction; the original snapshot is reverified. Build files,
wrappers, JARs, Kotlin and other files are not copied. CodeQL runs with build mode none
and the copied tree as source root, retaining existing sanitized environment, timeout
and resource controls. Candidate locations still bind to the original snapshot paths
and hashes; evidence reads original snapshot files.

Reports disclose java-source-only-v1, omitted-file count, unresolved dependencies,
unqualified generated code and unselected languages. Both Java profiles remain
incomplete. Batch skip-existing is profile-specific; comparisons flag differing
extraction profiles. Historical reports remain immutable. No schema migration.

This avoids exposing repository build descriptors/scripts to dependency discovery.
It is not an OS sandbox or network-denial mechanism. CodeQL's own inference/dependency
behavior is not thereby qualified; production needs enforced network/resource policies.
Supplied JARs and build configuration do not contribute semantic coverage. Generated
Java already present is scanned without proving it matches the intended build.

## Validation and usage

```sh
veriflow scan-run RUN_ID QUERY_PATH --language java --java-profile source-only
uv run python scripts/validate_spring.py QUERY_PATH work/maven-acceptance --java-profile source-only --project-layout maven
uv run python scripts/validate_spring.py QUERY_PATH work/gradle-acceptance --java-profile source-only --project-layout gradle
```

Use the installed Java SqlTainted.ql query and new output directories. Each real suite
checks vulnerable/fixed/foreign-annotation/malformed cases, retained source-to-sink
paths and local advisory gates. Maven-layout fixtures include a POM; Gradle-layout
fixtures contain a build script that throws if evaluated. Neither descriptor is copied.
No fixture build or live model call is requested. Unit tests check copy contents,
explicit omitted coverage, invalid profile selection and profile-specific skip behavior.

Local Maven is installed; Gradle is absent. Neither is needed for this source-only
profile. Full Maven/Gradle build qualification still requires a separately isolated
execution environment and approved dependency access. This is the next prerequisite,
not a claim that arbitrary enterprise builds work on this laptop.

## Reference

GitHub documents that Java none mode can invoke Maven/Gradle for dependency inspection:
[CodeQL compiled-language build options](https://docs.github.com/en/enterprise-cloud%40latest/code-security/reference/code-scanning/codeql/build-options-for-compiled-languages).
That behavior is why this profile gives CodeQL a Java-only copy instead of simply
removing the existing descriptor rejection.

Validation completed: all eight real layout cases passed; 394 regression tests passed.
