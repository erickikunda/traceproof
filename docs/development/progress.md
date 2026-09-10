# Implementation progress after Slice 23

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

**Planning estimate: approximately 25–30% of the full implementation plan and 60–65%
of M0–M2.** The rounded conversational estimates are about one quarter overall and
about three fifths of the laptop milestone scope. These are feature-delivery estimates,
not percentages of elapsed effort, calendar duration, production readiness or quality.

The plan contains 64 work packages. The simple rubric below assigns implemented work
1 point, partial work 0.5 and unimplemented work 0. It deliberately gives no credit for
architecture prose alone. Work packages differ greatly in effort, so the result is a
rough progress indicator, not an earned-value forecast or release acceptance decision.

| Milestone | Packages | Implemented | Partial | Unimplemented | Credit |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0: contracts and prerequisites | 8 | 2 | 6 | 0 | 5 / 8 |
| M1: intake and durable execution | 7 | 3 | 1 | 3 | 3.5 / 7 |
| M2: scan-to-report POC | 10 | 4 | 6 | 0 | 7 / 10 |
| M3: quality and reuse | 9 | 0 | 3 | 6 | 1.5 / 9 |
| M4: benchmark reporting | 8 | 0 | 5 | 3 | 2.5 / 8 |
| M5: multiworker and portfolio exports | 8 | 0 | 0 | 8 | 0 / 8 |
| M6: OpenShift pilot | 7 | 0 | 0 | 7 | 0 / 7 |
| M7: production qualification | 7 | 0 | 0 | 7 | 0 / 7 |
| **Total** | **64** | **9** | **21** | **34** | **19.5 / 64 ≈ 30%** |

M0–M2 receive 15.5 / 25 points, or 62%. The source-only CLI path is usable, but the full
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
| M1.3, M1.6, M1.7 | Unimplemented: Git acquisition, explicit pause/cancel controls, PostgreSQL contract qualification |
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
