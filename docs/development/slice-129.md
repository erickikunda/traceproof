# Slice 129 — Java/Spring file-path candidates

Adds java-spring-file-path-v1 with exact Files.readAllBytes(Path) sink and the established
bounded Spring GET/String RequestParam source. Native Path.of propagation is evaluated with
direct and cross-file input; no all-string or name-only fallback is introduced. Existing
JDBC profile/default behavior and advisory policies remain unchanged. Reports use existing
projection 15 CWE/profile fields. No schema migration or image update.

Six native cases expect 1/0/1/0/0/1 candidates: vulnerable, constant fixed, cross-file,
disconnected, foreign lookalike sink and guard-present uncertain. Source and query provenance
are retained by the shared pipeline. All outcomes remain incomplete coverage; CWE-22
candidates do not prove directory escape. Evidence/report exports have no LLM calls.

Validation runs with UID 1000710000, read-only root, dropped capabilities, bounded resources
and network none, using a new wheel installed into disposable scratch. Results are in
work/slice129-reports/validation.json; focused existing Joern/workflow/claim tests: 71 passed.
No full suite repeat: no shared report/parser changes since the 1,040-test baseline.

All six native cases passed with the expected counts and persisted report exports.

Next Slice 130: bounded Python/Flask SSRF discovery (CWE-918), preserving unknown destination,
redirect/DNS and deployment egress facts rather than inferring exploitability.
