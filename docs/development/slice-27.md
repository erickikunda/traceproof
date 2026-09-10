# Slice 27: verified original SARIF export

```bash
uv run traceproof get-sarif REPO_ID ATTEMPT_ID > results.sarif
```

This read-only command returns the original SARIF bytes, without a JSON wrapper or
added newline. Repository ownership of the exact query attempt is checked first.
Use `scan-history`, `scan-run`, or a published report's `attempt_id` to discover the ID.
There is no latest-selection fallback and no CodeQL/model execution.

Only completed or partial attempts with a recorded SARIF digest are eligible. The
fixed local artifact path is derived from the attempt identity, ignoring paths in
stored tool output. Retrieval rejects linked paths, nonregular files, missing files,
files exceeding 16 MiB and SHA-256 mismatches. Validation finishes before any artifact
bytes are written to stdout. Errors go to stderr and exit 1. Shell redirection itself
can create/truncate the destination even on failure; always check exit status.

Raw SARIF is an explicit operator export, not the sanitized dashboard projection.
It may retain messages, paths, flows and diagnostics with sensitive repository details.
Export only to an appropriate local destination and review before sharing. No SARIF
URI is fetched or executed. Viewer compatibility depends on the consumer; this slice
preserves CodeQL output rather than certifying a particular viewer or cloud upload.

Partial output remains partial. Candidate alerts are not confirmed vulnerabilities,
and an empty results array is not a clean verdict. Use the matching TraceProof report
for readiness, limitations and advisory/operator state; these are not injected into
the original CodeQL SARIF. Historical files removed by retention cannot be recreated
by this command. Local OS permissions remain the access boundary.

Tests cover byte-exact CLI output, repository scope, partial output, ignored stored
paths, altered/missing/oversized files, file and directory symlinks, FIFO rejection,
failed attempts and missing digests. No database migration is needed.
