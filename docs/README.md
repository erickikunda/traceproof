# TraceProof documentation

Start with the [CLI user/operator guide](guides/cli-operator-guide.md) for the laptop workflow,
status interpretation, reports and recovery. The API companion guide will ship with the
first hosted API, as scheduled in the implementation plan.

**Current priority:** multi-language coverage before further CLI refinements. The revised
plan starts with shared adapter contracts and Java/Spring, followed by C#/ASP.NET,
JavaScript/TypeScript, Rust, Go and mixed-language qualification. Slice 37 adds dependency-free Java static scanning alongside Python; Java semantic
indexing, LLM evidence and Spring builds remain unqualified.

- [System design](architecture/system-design.md): leadership use cases, swimlane,
  data-flow/sequence diagrams, evidence policy, report contracts and enterprise architecture.
- [Implementation plan](plans/implementation-plan.md): milestones M0–M7 and acceptance gates.
- [Local intake decision](decisions/0001-local-intake-slice.md): the boundary of the first slice.
- [First-slice status](development/slice-01.md): implemented behavior, validation and remaining work.
- [Second-slice status](development/slice-02.md): Python inventory, coverage reports and CodeQL diagnostics.
- [Third-slice status](development/slice-03.md): call candidates, bounded evidence and CodeQL security queries.
- [Fourth-slice status](development/slice-04.md): immutable context bundles, advisory triage and budget accounting.
- [Fifth-slice status](development/slice-05.md): source claim checks and explicit bounded context expansion.
- [Sixth-slice status](development/slice-06.md): conservative Flask modeled-source mapping and regression coverage.
- [Seventh-slice status](development/slice-07.md): immutable repository summaries and JSON/HTML/Markdown/CSV exports.
- [Eighth-slice status](development/slice-08.md): conservative report comparisons and occurrence references.
- [Ninth-slice status](development/slice-09.md): real CodeQL acceptance fixtures and explicit static-review readiness.
- [Tenth-slice status](development/slice-10.md): separate benchmark manifest/label contracts and offline alignment checks.
- [Eleventh-slice status](development/slice-11.md): pinned offline candidate-location scorecards with explicit uncertainty.
- [Twelfth-slice status](development/slice-12.md): append-only operator reviews, revision checks and report projections.
- [Thirteenth-slice status](development/slice-13.md): opt-in Anthropic Messages adapter with shared evidence and budget controls.
- [Fourteenth-slice status](development/slice-14.md): explicit latest-attempt/latest-completed selection with current-work disclosure.
- [Fifteenth-slice status](development/slice-15.md): CLI operator guide and verified synthetic walkthrough; API guide delivery gate.
- [Sixteenth-slice status](development/slice-16.md): paginated repository runs and query attempts, including unpublished work.
- [Seventeenth-slice status](development/slice-17.md): benchmark summary/repository/label/candidate CSV exports for dashboards.
- [Eighteenth-slice status](development/slice-18.md): per-CWE benchmark proxy metrics with explicit missing-label and incomplete states.
- [Nineteenth-slice status](development/slice-19.md): durable benchmark publication, history and exact retrieval with integrity checks.
- [Twentieth-slice status](development/slice-20.md): compatibility-gated comparison of saved benchmark scorecards.
- [Twenty-first-slice status](development/slice-21.md): source-only scan orchestration with prerequisite gates and exact-attempt publication.
- [Twenty-second-slice status](development/slice-22.md): local prerequisite diagnostics and operator actions without tool execution.
- [Twenty-third-slice status](development/slice-23.md): loopback-only Ollama adapter for local POC inference.
- [Twenty-fourth-slice status](development/slice-24.md): fixed per-run request limits, including zero-priced local model work.
- [Twenty-fifth-slice status](development/slice-25.md): bounded sequential import scanning with per-row outcomes and explicit rescans.
- [Progress assessment](development/progress.md): work-package estimates against the full implementation plan.
- [Twenty-sixth-slice status](development/slice-26.md): read-only import report inventory and CSV dashboard export.

The design and plan are proposals; the slice status and README describe what actually runs.

- [Twenty-seventh-slice status](development/slice-27.md): verified original SARIF export for exact query attempts.
- [Twenty-eighth-slice status](development/slice-28.md): explicit, recorded CodeQL thread and RAM settings.
- [Twenty-ninth-slice status](development/slice-29.md): self-contained HTML benchmark scorecards for sharing.
- [Thirtieth-slice status](development/slice-30.md): bounded sequential candidate triage with stable keys and stop rules.
- [Thirty-first-slice status](development/slice-31.md): durable import dispatch pause/resume with audit history.
- [Thirty-second-slice status](development/slice-32.md): terminal import dispatch cancellation with completed-work retention.
- [Thirty-third-slice status](development/slice-33.md): paginated import history with dispatch filters and intake counts.
- [Thirty-fourth-slice status](development/slice-34.md): CodeQL extraction history, including failures before query analysis.
- [Thirty-fifth-slice status](development/slice-35.md): bounded storage inventory and artifact-reference audit without deletion.
- [Thirty-seventh-slice status](development/slice-37.md): shared language coverage and initial Java static scanning.
- [Thirty-sixth-slice status](development/slice-36.md): conservative Flask request alias mapping in evidence gate 3.

- [Slice 38](development/slice-38.md): bounded Java syntax indexing and parse coverage.

- [Slice 39](development/slice-39.md): Spring annotation syntax evidence inventory.

- [Slice 40](development/slice-40.md): source-only Spring-style SQL path acceptance.

- [Slice 41](development/slice-41.md): Java SQL advisory evidence gate.
