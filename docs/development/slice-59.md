# Slice 59 — Scanner execution boundary and Joern-first plan

## Delivered

The implementation plan now prioritizes scanner portability, Joern-first qualification,
early C#/Rust acceptance gates, and an equivalent Opengrep comparison. Full C and C++
support follows the existing language work plan, with small feasibility cases included
in engine qualification now. No automatic dual-engine scan is required.

`scanner.py` defines immutable execution request/result records and a callable protocol.
`codeql_scanner.py` owns CodeQL discovery, version probing, process launch, restricted
environment, offline arguments, logs and process-group timeout handling. `scanning.py`
invokes it and retains durable attempt creation, source/query integrity verification,
SARIF normalization and atomic candidate publication. Existing report fields and CLI
arguments remain unchanged. Process completion does not imply complete coverage.

## Validation

- Full suite: 484 passed; one existing duplicate-ZIP fixture warning.
- Existing durable outcome tests cover success, empty, partial, malformed output,
  failed queries and timeouts; secret environment variables remain excluded.
- Added unavailable/unlaunchable adapter tests: neither produces successful empty results.
- Ruff lint/format, diff whitespace check, and source/wheel build pass.
- Code index refreshed.

No new real-engine or container run was performed for this boundary-only refactor.
Earlier Slice 58 Linux fixture evidence remains separate; it is not Joern qualification.

## Boundaries and next step

No migration, new scanner installation, or LLM call. CodeQL remains the only runnable
backend. Extraction and prepared-input storage still use CodeQL; normalization and
qualified triage are not yet generic. The execution protocol alone does not establish
backend interchangeability or change evidence gates.

Next: S2 in plan §18 — explicit engine identity/capabilities, prepared-input provenance,
backend routing and engine-aware reuse, with historical CodeQL compatibility. Then a
pinned Joern Java/Spring source-to-report fixture. Do not equate rule IDs or CWE labels
across engines, fabricate flow paths, or promote discovery-only output into qualified
advisory evidence.
