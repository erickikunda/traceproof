# Implementation progress after Slice 46

## Priority reset — 10 September 2026

The [implementation plan v0.2](../plans/implementation-plan.md) now prioritizes Java/Spring,
C#/ASP.NET, JavaScript/TypeScript, Rust and Go over further CLI refinement. Slice 37 delivers shared language selection/coverage and a dependency-free Java static
scan-to-report fixture. L0/L1 remain partial: Java semantic indexing, evidence qualification
and Spring/Maven/Gradle profiles come next, followed by the sequence in plan §2.

The estimates and 64-package table below are a **historical baseline for the former scope**.
M3.1 has expanded into seven substantial subpackages; no current expanded-scope completion
percentage is asserted until these are re-estimated. Existing implementation evidence remains
valid, but added scope does not earn completion credit. Defer discretionary CLI/report/storage
enhancements; retain necessary correctness/security fixes and language-workflow documentation.

Slice 38 adds bounded, resumable Java syntax indexing and pre-extraction parse gates.
Java semantic resolution, evidence policies and Spring remain unqualified.

Slice 39 adds snapshot-bound Spring annotation syntax observations; runtime binding,
Java LLM evidence and framework extraction qualification remain open.

Slice 40 adds real source-only Spring-style SQL path acceptance with vulnerable,
fixed, foreign-annotation and malformed-source cases. Built Spring and Java LLM
evidence qualification remain open; L1 is still partial.

Slice 41 adds a narrow Java SQL advisory gate for retained RequestParam-to-executeQuery
flows. Broader Java evidence and built Spring qualification remain pending.

Slice 42 lets Java advisory gates use complete context assembled from bounded
evidence expansions. Build qualification and broader language coverage remain open.

Slice 43 adds explicit Java-only copied-source extraction for Maven/Gradle layouts.
This does not qualify builds; isolated build execution and approved dependencies remain
prerequisites. L1 remains partial.

Slice 44 adds opt-in automatic selection for one detected supported source language.
Mixed-language execution and query routing remain pending.

Slice 45 starts L2 with opt-in C# source-only extraction/reporting. SDK/NuGet behavior
requires explicit download consent. Classic ASP.NET detection qualification has a known
miss; C# evidence and both ASP.NET framework lanes remain unqualified.

Slice 46 resolves the specific classic ASP.NET fixture miss with pinned framework
references and SDK. The classic vulnerable/fixed pair now passes under externally
enforced macOS network denial (1/0 candidates). Slice 47 adds application-managed macOS extraction network isolation. Linux container
qualification and broader C# evidence/framework qualification remain open.

## Historical delivery assessment

Slice 36 extends conservative Flask source mapping to request aliases in evidence gate 3.
M3.2 remains partial; no corpus recall measurement or additional package credit is claimed.

Slice 35 adds a bounded storage/reference inventory. M1.4 remains partial: automated
orphan cleanup and retention are still open. No additional package credit is claimed.

Slice 34 adds extraction-attempt history and timestamps for new extraction records.
This improves recovery visibility without additional work-package credit.

Slice 33 adds paginated import discovery with dispatch state and intake counts. It extends
local operational visibility without additional package credit.

Slice 32 adds terminal import dispatch cancellation. M1.6 remains partial because full
run/process and distributed cancellation are not implemented; package credit is unchanged.

Slice 31 adds durable import dispatch pause/resume and audit history. M1.6 is now partial:
running processes are not interrupted, and cancellation/distributed controls remain open.

Slice 30 adds bounded exact-attempt triage orchestration using existing model/evidence
and budget gates. No new detection-quality or milestone credit is claimed.

Slice 29 adds a self-contained HTML benchmark scorecard. M4.7 remains partial at the full
acceptance level; no bank benchmark or additional package credit is claimed.

Slice 28 adds configurable, recorded CodeQL resource requests. This prepares local
tuning but does not qualify capacity or container enforcement; package credit is unchanged.

Slice 27 adds integrity-checked original SARIF retrieval for exact repository/attempt
identities. M2.8 remains partial because the full finding/coverage contract is still open;
package credit is unchanged.

Slice 26 adds read-only import report inventory and CSV export, scoped to admitted runs
with explicit missing-report states. Local reporting improves; package credit is unchanged.

Slice 25 adds bounded sequential import scanning. This is local orchestration, not
distributed scheduling or throughput qualification; package credit is unchanged.

Slice 24 adds durable request limits alongside monetary budgets, including zero-priced
local inference. This strengthens the existing local controls without new package credit.

Slice 23 adds local Ollama inference for POC testing; no additional detection-quality
or enterprise-qualification credit is claimed.

Slice 22 adds local prerequisite diagnostics. M0 environment qualification remains partial;
no additional work-package credit is claimed.

Slice 21 combines the existing source-only stages behind `scan-run` with prerequisite
gates and exact-attempt publication. It adds no new detection coverage or package credit.

Slices 15–16 add the verified CLI guide, an API documentation delivery gate and repository
run/query-attempt histories. These extend existing partial packages; work-package credit
below remains unchanged.

Slice 17 adds benchmark CSV projections at four explicit grains. M4.6 remains partial:
persisted scorecards and full adjudicated quality measures remain open. Slice 18 adds
per-CWE proxy metrics with explicit no-label/incomplete states; package credit remains partial.

Slice 19 adds durable scorecard publication/history/retrieval. Persisted proxy reports now
exist; full adjudicated quality measures and benchmark qualification still remain open.
No additional work-package credit is claimed.

**Historical planning estimate for the former scope: approximately 31% overall and 64%
of M0–M2.** These are feature-delivery estimates,
not percentages of elapsed effort, calendar duration, production readiness or quality.

The plan contains 64 work packages. The simple rubric below assigns implemented work
1 point, partial work 0.5 and unimplemented work 0. It deliberately gives no credit for
architecture prose alone. Work packages differ greatly in effort, so the result is a
rough progress indicator, not an earned-value forecast or release acceptance decision.

| Milestone | Packages | Implemented | Partial | Unimplemented | Credit |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0: contracts and prerequisites | 8 | 2 | 6 | 0 | 5 / 8 |
| M1: intake and durable execution | 7 | 3 | 2 | 2 | 4 / 7 |
| M2: scan-to-report POC | 10 | 4 | 6 | 0 | 7 / 10 |
| M3: quality and reuse | 9 | 0 | 3 | 6 | 1.5 / 9 |
| M4: benchmark reporting | 8 | 0 | 5 | 3 | 2.5 / 8 |
| M5: multiworker and portfolio exports | 8 | 0 | 0 | 8 | 0 / 8 |
| M6: OpenShift pilot | 7 | 0 | 0 | 7 | 0 / 7 |
| M7: production qualification | 7 | 0 | 0 | 7 | 0 / 7 |
| **Total** | **64** | **9** | **22** | **33** | **20 / 64 ≈ 31%** |

M0–M2 receive 16 / 25 points, or 64%. The source-only CLI path is usable, but the full
milestones include work beyond that narrow demonstration. No entire milestone is
declared accepted merely because its central demonstration works.

## Work-package assessment

| Packages | Status and evidence/remaining scope |
| --- | --- |
| M0.1–M0.5, M0.8 | Partial: pinned Python/local CodeQL, typed runtime contracts and synthetic tests exist; broader environment qualification, static type checking, complete schemas/adapter contracts and a full requirement-to-test register remain |
| M0.6 | Implemented local Python scope: reproducible vulnerable/fixed/incomplete fixtures exercised with real CodeQL and report assertions |
| M0.7 | Implemented initial local scope: separate manifest/label schemas, strict validation, pinned identities and optional stored-metadata alignment; no dataset registration or evaluation |
| M1.1, M1.2, M1.5 | Implemented local scope: CSV admission, safe archive snapshots, SQLite single-worker persistence/checkpoints/recovery |
| M1.4 | Partial: immutable artifacts exist; automated orphan cleanup does not |
| M1.6 | Partial: durable import dispatch pause/resume with audit history; run cancellation and distributed execution controls remain |
| M1.3, M1.7 | Unimplemented: Git acquisition and PostgreSQL contract qualification |
| M2.1, M2.2 | Implemented local Python scope: inventory/conservative resolution, CodeQL extraction/query execution and candidate ingestion |
| M2.3, M2.4 | Partial: index gates/bundles exist; full coverage obligations and security-map semantics remain |
| M2.5 | Partial: replay and opt-in OpenAI/Anthropic transports exist; live gateway compatibility has not been validated |
| M2.6 | Partial: bounded advisory triage and two class policies exist; broader evidence/accepted-verdict semantics remain |
| M2.7 | Partial: exact occurrence references and advisory history exist; stable reviewed finding-family records across edits remain |
| M2.8 | Partial: immutable reports, formats and explicit latest-completed selection with freshness disclosure exist; full finding/coverage report contract remains |
| M2.9, M2.10 | Implemented local scope: scan/candidate CSV exports and single-worker reservations/stop rules |
| M3.2, M3.7 | Partial: narrow Flask source mapping and conservative observation comparison; broader models and coverage-qualified resolution remain |
| M3.8 | Partial: append-only local operator review assertions, evidence ownership, revision checks and report history; authenticated reviewers, suppression expiry and rule-gap records remain |
| Other M3 packages | Unimplemented at the stated acceptance level: Java/Spring, independent exploration/review, dependency/secret adapters, layered cache invalidation and measured cost/quality ablations. Anthropic transport exists, but selective independent review in M3.4 does not; no additional package credit is claimed |
| M4.3, M4.5–M4.7 | Partial: pinned offline report selection, conservative location matching and JSON/Markdown recall-proxy scorecards; full scan configuration, structural/adjudicated matching, per-class metrics and persisted multi-format scorecards remain |
| M4.8 | Partial: compatible saved scorecard comparison and provisional label transitions; cost/latency, model attribution and adjudicated regression gates remain |
| M4.1, M4.2, M4.4 | Unimplemented operationally: durable corpus registration/applicability review and evaluator-only scan dispatch |
| M5–M7 | Unimplemented operationally: distributed orchestration, GCS, enterprise authorization, OpenShift and production load/recovery/quality qualification |

## What the percentages do not establish

There has been no benchmark run against the 50-repository ground truth, no live bank
gateway validation and no demonstrated 1,000-repositories/day throughput. SQLite tests
and local locking are not substitutes for PostgreSQL reservations, Redis coordination
or OpenShift isolation. The largest enterprise and operational risks are still ahead.

The next priorities are complete evidence/coverage and finding-state contracts,
benchmark evaluation
and enterprise-compatible model integration. Update this assessment as acceptance
evidence accumulates; do not increment the percentage simply because another slice
has been numbered or committed.

Slice 48 begins OCP-1 locally: UBI/Linux ARM64 image and restricted Docker Python
acceptance. Actual bank OCP validation is deferred to functional POC completion by
request, and remains required. Other language toolchains and deployment manifests
remain unqualified in Linux.

Slice 49 extends Linux qualification to basic source-only Java using a pinned full
Java 21 JDK. Offline Spring is NOT qualified: the vulnerable case produces zero
candidates with blocked inferred Maven downloads and unresolved annotations. Historical
macOS Spring runs fetched dependencies despite source-only input. Next: pinned Java
profiles and offline Spring requalification. Full builds and Linux C# remain open.
Container suite selection and package inventories use TraceProof's virtual environment.

Slice 50 supplies pinned local Maven-layout JAR profiles for Java, records profile
identity in reuse/reports and rechecks integrity after extraction. Six pinned Spring
JARs restore the offline flat Spring fixture. Other inferred fetch attempts remain
blocked by the container; the profile itself does not enforce network isolation.
