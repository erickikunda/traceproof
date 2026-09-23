# Slice 04 — Evidence bundles and bounded advisory triage

Slice 03 is committed as `5f29400`. This slice implements the first bounded context and
triage loop across M2.4, M2.5, M2.6 and M2.10. It provides replay and an opt-in OpenAI
Responses adapter, strict response validation, explicit abstention, and durable cost
reservations. It does not complete M2 or establish vulnerability detection accuracy.

## Workflow

```mermaid
sequenceDiagram
    actor Operator
    participant CLI
    participant Artifacts as Snapshot and SARIF
    participant DB as SQLite ledger
    participant Adapter as Replay or opt-in provider
    Operator->>CLI: build-bundle(attempt, fingerprint)
    CLI->>Artifacts: Verify source and SARIF digests
    CLI->>CLI: Select bounded primary/flow/related excerpts
    CLI->>DB: Persist content-addressed bundle
    Operator->>CLI: triage-budget(run, cap)
    CLI->>DB: Fix per-run budget
    Operator->>CLI: triage(bundle, config, key)
    CLI->>DB: Verify bundle and check idempotency
    alt Evidence incomplete or budget exhausted
        CLI->>DB: Record abstention; no model call
    else Eligible request
        CLI->>DB: Commit conservative reservation
        CLI->>Adapter: One bounded structured request
        Adapter-->>CLI: Decision, refusal/incomplete status, usage
        CLI->>CLI: Validate schema, citations and rationale
        CLI->>DB: Persist advisory result and accounting
    end
    Operator->>CLI: triage-report(run)
    CLI->>DB: Read only
    CLI-->>Operator: Decisions, usage and remaining budget
```

## Context and evidence contract

`build-bundle ATTEMPT_ID FINGERPRINT` joins the normalized candidate to its original
SARIF result using the existing snapshot/tool/rule/result fingerprint. It verifies the
stored SARIF SHA-256 and snapshot against the admitted DB manifest. It selects primary,
flow and related locations in SARIF order, with no repository-supplied instructions.

Limits: eight considered locations, 40 lines in each original region plus three context
lines on either side, 1 MiB per source file, 16 KiB combined source text, 2 KiB of candidate
message, and a 32 KiB canonical JSON envelope. Excerpts retain snapshot/file digest,
original region and actual excerpt range. Source lines use universal newline handling;
Unicode separators inside comments do not shift line numbers.

Missing/unmapped locations, oversized regions/files, unsupported encodings, omitted
locations and source/message budget limits produce explicit gaps. Source or SARIF
integrity failure aborts publication. A bundle with gaps is `partial`; triage abstains
without invoking a provider. `ready` means the bounded context was materialized without
those gaps, not that the flow is feasible or the available context proves a vulnerability.

Bundle ID is SHA-256 of its canonical content, including builder version, classification,
run/snapshot/attempt/fingerprint and snippets. Rebuilds reuse the same record when identical.
Retrieval verifies that content hash and does not reread source. The source is included
as `trust=untrusted_source_and_tool_output`. No benchmark labels enter the bundle.

## Adapter and decision contract

The provider-independent `Adapter` protocol returns a strict `Reply`: status, optional
decision and optional usage. The built-in replay adapter reads a capped response fixture
and includes its digest in request identity. Replay is an orchestration test, never a
security assessment, and all resulting ledger rows are marked `simulated=true`.

The OpenAI adapter implements the documented [Responses request contract](https://developers.openai.com/api/reference/python/resources/responses/methods/create):
`text.format` carries a strict JSON schema, `max_output_tokens` bounds generation,
`store=false`, truncation is disabled, and no tools are supplied. The prompt separates
trusted triage instructions from untrusted evidence and asks for counterevidence and
abstention. This is a defense, not a proof of prompt-injection immunity. Provider retention
and bank data-handling controls still require enterprise approval; `store=false` alone
does not establish an enterprise retention policy.

The HTTPS request runs in an isolated Python subprocess with a hard parent timeout of
the configured network timeout plus three seconds. Only the designated key environment
variable is forwarded. HTTPS certificate validation is enabled, redirects are rejected,
environment proxy settings are not inherited, and replies are capped at 128 KiB. There
are no automatic retries or provider tools. The optional `ca_file` supports a trusted
enterprise CA bundle. Proxy authentication, mTLS, Entra authentication and Anthropic
transport are not implemented yet.

Decision fields are `verdict`, `rationale`, `evidence_ids`, `counterevidence`. Supported
verdicts are `needs_review`, `likely_false_positive`, `abstain`. Non-abstention requires
at least one valid bundle evidence ID; likely-false-positive suggestions additionally
require nonempty counterevidence. Unknown citations, invalid structures or blank rationale
are rejected. No decision changes the original candidate's `adjudication=unreviewed` or
establishes a verified finding. Citation membership is checked, not semantic entailment;
class-specific evidence obligations and human review remain necessary.

## Operator configuration

Run `veriflow init` to apply migration 0004. Offline examples are committed in
`examples/triage-replay-config.json` and `examples/triage-replay-response.json`.

For live validation, create a local JSON policy with these fields:

| Field | Meaning |
| --- | --- |
| `provider` | `openai` for live; `replay` for offline |
| `model` | Explicit approved model/deployment identifier; no default model |
| `endpoint` | Exact HTTPS Responses endpoint, without userinfo/query/fragment |
| `allowed_endpoint_hosts` | Explicit hostname allowlist containing that endpoint |
| `allowed_classifications` | Source classifications permitted for this adapter; default only synthetic |
| `allow_source_transmission` | Must explicitly be true for live use; defaults false |
| `api_key_env` | Environment-variable name only; default `TRACEPROOF_OPENAI_API_KEY` |
| `ca_file` | Optional trusted CA bundle path |
| `max_output_tokens` | 128–8,192; default 1,024 |
| `timeout_seconds` | 1–120; default 60 |
| `input_micro_usd_per_1k`, `output_micro_usd_per_1k` | Operator-supplied rates; live rates cannot both be zero |

No model identifier, endpoint, bank credential or market price is assumed. Prices are
integer micro-USD per 1,000 tokens. One USD equals 1,000,000 micro-USD. Replay example
rates are fictional accounting inputs, not provider-price guidance.
Keep the actual key in the named local environment variable, never in the policy file,
CSV, source archive or chat. Config validation failures omit raw values from CLI errors.

```bash
uv run veriflow build-bundle ATTEMPT_ID CANDIDATE_FINGERPRINT
uv run veriflow triage-budget RUN_ID 100000
uv run veriflow triage BUNDLE_ID examples/triage-replay-config.json demo-1 \
  --replay examples/triage-replay-response.json
uv run veriflow triage-report RUN_ID
# For an explicitly configured live policy, omit --replay:
# uv run veriflow triage BUNDLE_ID /absolute/local-policy.json live-1
```

## Reservation and recovery semantics

Migration 0004 adds evidence bundles, one immutable budget per run and an append-only
request ledger with a unique `(run_id, request_key)`. A local exclusive worker lock covers
the whole triage operation. The request digest includes bundle content, prompt/schema,
policy, model, adapter identity and replay-fixture digest. Identical keys reuse the result;
different content under the same key fails. A caller cannot reset a run budget by changing
the key or policy.

Before invocation, reserve the configured price of the request's UTF-8 JSON byte count
plus 4,096 input-token allowance and the maximum output tokens. This is a conservative
estimate, not a provider tokenizer or a billing guarantee. All arithmetic uses integer
micro-USD with upward rounding. Usage, when present, settles the reservation using the
recorded rates. Cached-token discounts and other provider-specific billing are not modeled.
Actual usage exceeding the reservation is charged in full and flagged; further requests
cannot ignore an overdrawn budget. A provider's true billing still requires reconciliation.

Timeouts, process death, malformed transport output or missing usage keep the full
reservation because a charge may already have occurred. A later triage operation marks
abandoned running entries `unknown` without retrying them or releasing their reservations.
Read-only reports can still show `running` before that recovery occurs. There is no automatic
reconciliation or manual refund command yet. Budget-exhausted and incomplete-evidence entries
invoke no model and account zero cost. Replay accounting is simulated; aggregate accounted
amounts are budget consumption, not an invoice or a statement of actual spend.

States include `completed`, `refused`, `incomplete`, `invalid_output`, `invalid_citations`,
`invalid_rationale`, `incomplete_evidence`, `budget_exhausted`, `unknown`,
`reservation_exceeded`, and transient `running`. Reports retain classification, prompt/config
digests, model/adapter identity, rates, usage and advisory disposition. Refusal/incompleteness
never produces a clean result. No retries, context expansion or autonomous follow-on calls
occur in this slice.

## Validation and remaining work

The existing synthetic CodeQL injection result produced a ready bundle with seven snippets.
The offline replay path reserved 11,166 simulated micro-USD and settled 660 from the fixture's
500 input/80 output tokens. It returned abstain, and repeated retrieval did not invoke a
model. No paid/live provider request was made.

Tests cover flow/primary excerpts, integrity and location gaps, budgets and exact rounding,
replay/idempotency, classification and endpoint policy, citation/rationale gates, refusal,
missing usage, overrun, CLI behavior, HTTP request/response contracts with mocks, and an
actual process-death recovery test. Source/candidate state remains unchanged by triage.
Validation: **128 tests passed**; Ruff lint/format checks and package builds passed. The
one warning is the intentional duplicate-path ZIP rejection fixture inherited from Slice 01.

No blocker exists for the offline POC. Live end-to-end validation requires the user's
approved endpoint/model, accurate pricing, and a key supplied locally through the configured
environment variable. Transport mocks do not establish compatibility with a bank gateway.

Next: class-specific evidence obligations and semantic citation checks, evidence expansion
under a measured budget, Anthropic/gateway integration, and benchmark-based quality evaluation.
Also pending: full query-pack provenance, shared PostgreSQL reservations, Redis rate limits,
OpenShift worker isolation, billing reconciliation and throughput benchmarks. The system
still makes no claim of handling 1,000 repositories/day or meeting measured recall/precision
targets. This slice leaves M2 partially implemented.
