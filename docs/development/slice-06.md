# Slice 06 — Flask modeled-source mapping

Slice 05 is committed as `98ffc9e`. This slice addresses the concrete CodeQL source
representation gap found during its smoke test. A modeled Flask flow can begin at the
`request` import rather than the later `request.args` expression. The previous gate
rejected that shape despite retaining both the input access and sink.

## Acceptance boundary

The existing direct-source path remains available. The additional mapping requires:

- A single top-level, absolute `from flask import request` binding with its normal name.
- Complete source-file text reconstructed from consistent, overlapping bundle excerpts.
- No syntactic rebinding of `request`, conflicting import, or wildcard import anywhere
  in that file. Assignments, parameters, definitions, exception targets and pattern
  captures are included in this conservative check, even in unrelated scopes.
- Every flow step preceding the recognized input access retained in the same file and
  thread and located exactly on that import statement.
- A recognized Flask request access at the quoted source location and the existing
  sink/flow/guard obligations, with the sink at the last step of the same thread.

Supported Flask access syntax is `request.args`, `form`, `data`, `json`, and
`request.get_json`. Aliases, cross-file prefixes, intervening non-import steps, partial
files and other modeled sources do not use this mapping. They remain candidates with
an abstaining disposition when no other supported evidence path is available.

The gate records `source_mappings` with mapping kind, thread, import evidence IDs and
access evidence ID. These deterministic supporting references come from the verified
bundle; they do not require the model to invent additional import claims. Both
`binding_proven` and `reachability_proven` remain false. Static syntax cannot establish
runtime binding identity, exclude monkey-patching, establish taint or prove guard
effectiveness. Even a likely-false-positive suggestion never suppresses a candidate.

## Storage, cost and compatibility

Builder version 3 adds `source_line_count` to each original snippet. It comes from the
digest-verified file and allows the gate to distinguish complete evidence from an
excerpt that merely parses. Explicit expansion can fill missing lines within existing
limits; it does not remove inherited gaps. No additional file contents are automatically
sent to a provider. Source remains capped at 16 KiB and the bundle envelope at 32 KiB.

Gate version 2 participates in request identity. Prompt version remains 2 and its
requirements payload describes the mapping. Database schema remains 0004. Rebuild
historical bundles and use a new triage request key to exercise this gate; stored
historical decisions are not rewritten. Version 2 bundles still support the original
direct-source checks but lack line counts needed for this new mapping.

```bash
uv run traceproof build-bundle ATTEMPT_ID CANDIDATE_FINGERPRINT
uv run traceproof evidence-policy py/code-injection
uv run traceproof check-evidence NEW_BUNDLE_ID /absolute/decision.json
# Optional explicit replay uses the existing per-run budget:
uv run traceproof triage NEW_BUNDLE_ID examples/triage-replay-config.json new-request-key \
  --replay /absolute/replay-response.json
uv run traceproof triage-report RUN_ID
```

## Validation

All 167 tests passed, including 18 modeled-source regression cases. They cover the
four-step Flask trace, overlapping excerpts, rebinding forms, missing steps, unrelated
threads, incorrect imports, legacy metadata, incomplete files and conflicting text.
The inherited duplicate-path ZIP fixture produces one expected warning.

The saved CodeQL 2.27.0 synthetic injection result was rebuilt and passed the gate with
an operator-authored offline replay decision: `completed`, `needs_review`,
`supported_for_review`, `verified=false`. Its mapping connected import snippets E2/E3
to request access E4 and sink E5. Repeating the same key returned the identical ledger
result. Fictional replay usage settled 900 micro-USD of simulated budget; no live model
call or actual provider charge occurred. This exercises orchestration, not model accuracy.

No measured recall/precision or production-throughput claim follows from this fixture.
Broader source models and vulnerability classes, independent validation, benchmark
reporting, consolidated exports and production orchestration remain future slices.
