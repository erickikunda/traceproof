# Slice 49: Linux Java qualification and offline Spring dependency diagnosis

Slice 48 committed as 604c66b. This slice adds a checksum-pinned full Temurin
21.0.12.1+1 Linux ARM64 JDK, Java/Spring fixture suites and layout selection to the
restricted Docker acceptance runner. The image contains only the synthetic fixtures
needed by these suites. No Maven/Gradle build is executed. No database migration.

## Delivered behavior

The basic Java SQL vulnerable/fixed pair runs through syntax indexing, CodeQL and
report publication with expected 1/0 candidates. The existing Python suite remains
part of image acceptance. Runs retain arbitrary UID, read-only root, dropped
capabilities, no-new-privileges and no external network. Reports remain incomplete.

UBI shell activation previously selected /opt/app-root/bin/python instead of VeriFlow's
venv. The image now disables BASH_ENV activation and the runner uses the explicit venv
interpreter for scripts and package inventory. Report/structured fixture exports now
run on ordinary acceptance failures as well as successes; they do not convert failure
to success. OOM/hard-kill diagnostic limitations remain documented.

## Offline Spring failure — not qualified

The vulnerable Spring fixture produced zero candidates (expected one), while fixed,
lookalike and incomplete checks passed. The suite correctly exits nonzero. Installing
a full JDK did not fix the miss. Detailed javac-extractor logs show inferred downloads
of spring-web 6.0.10 and other Maven artifacts failing under denied networking, followed
by unresolved annotation symbols. The same query on the previously passing macOS
fixture had extractor-managed dependency fetches. The earlier source-only description
did not establish absence of dependency downloads; Slice 40 documentation is corrected.

The container does not silently enable network, add stub Spring classes or relax the
candidate expectation. --suite spring and its layout options remain diagnostic, not
qualified offline coverage. The next slice must add approved pinned Java dependency
profiles, record their identity in reuse/reporting, and repeat the offline matrix.
A full Maven/Gradle build profile is a separate requirement.

Evidence: work/slice49-spring-jdk-final retains failing structured checks and reports;
work/slice49-debug retains a diagnostic database and detailed logs. This diagnostic run
used a host-mounted synthetic state directory to preserve the database; it is not a
PVC/SQLite durability qualification. Standard acceptance state remains ephemeral.

The full JDK is pinned independently for a complete Java toolchain and future dependency
qualification; missing jmods was investigated but is not the demonstrated Spring cause.
JDK source: https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.12.1%2B1
No live model calls, bank source, image push or OCP access was used. OCP dev execution
remains deferred until functional POC completion, as requested. No user action is needed
for the dependency-profile implementation.

## Final checks

421 regression tests and lint/format checks passed. Final image build succeeded.
Python: all three cases passed (19.312 seconds). Java: both cases passed (36.09 seconds).
Spring: failed the vulnerable candidate-count check; this remains an open acceptance
gate, not an all-green suite. The package inventories include the actual VeriFlow
installation. Final image ID:
`sha256:2148e38fee5e586e4e703b8e617d472176e82b83a331b3a9f3203925ae745061`.
These synthetic timings are not throughput estimates.
