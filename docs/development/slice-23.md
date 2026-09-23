# Slice 23: local Ollama triage

The Ollama adapter uses the same `triage` command, bounded evidence, classification
policy, durable ledger, idempotency and claim gate as the other adapters. No database
migration is required. Existing replay/cloud request identities are preserved.

```bash
ollama list
uv run veriflow triage-budget RUN_ID 100000
uv run veriflow triage BUNDLE_ID examples/triage-ollama-config.json local-triage-1
uv run veriflow triage-report RUN_ID
uv run veriflow publish-report REPO_ID
```

The example selects the locally installed `LiquidAI/lfm2.5-1.2b-instruct:latest`. Change
`model` to a local completion model listed by your daemon. VeriFlow neither installs
nor downloads models. Start the Ollama service yourself if needed. Local tags can change;
retain the installed model digest separately when recording POC evaluation provenance.

The endpoint must be HTTP `/api/chat` on an explicitly allowed numeric loopback address
(`127.0.0.1` or `::1`) with an explicit port. The example uses port 11434. DNS names,
remote hosts, URL credentials/query strings and obvious cloud-model names are rejected.
Trust and configure the local daemon to use local models only: loopback addressing alone
cannot prove that a daemon or custom model alias does not relay requests elsewhere.

Source transmission must still be explicitly enabled, with permitted classifications.
No API key is required, read or forwarded. The isolated child receives an empty environment.
Inherited proxies and redirects are disabled; output is capped and requests have a total
timeout. There is no fallback, auto-retry, tool execution or model call from `scan-run`.

Requests use nonstreaming chat, a JSON schema, temperature zero, disabled thinking and
bounded `num_predict`. Schema definitions are inlined and numeric/string/array bounds
relaxed on the wire for local grammar compatibility; the original strict Decision schema
and evidence gate still validate output locally. Invalid JSON or claims abstain. Truncated
or non-final responses remain incomplete. Usage maps prompt/evaluation token counts to
the common ledger. Missing/invalid usage stays unknown.

`ollama_context_tokens` defaults to 32768 (4096–131072). A conservative request byte
estimate plus framing/output allowance must fit before dispatch; increase only within
your machine/model capacity or reduce the evidence request. This is not exact tokenizer
accounting or proof of the daemon's effective context. Output and timeout limits remain
the common settings (example: 1024 output tokens and 120 seconds).

Zero pricing is allowed for local compute, so the example's accounting is zero USD.
Hardware/electricity are not estimated, and a zero monetary rate does not bound the number
of manual calls. A run budget is still required. Ollama results are real inference, not
replay: `simulated` is false; existing `live_accounted_micro_usd` means non-replay
accounting and does not imply a paid cloud request. Small local models can abstain or
fail the evidence gate; successful transport is not measured vulnerability quality.

Offline tests cover policy, schema/context bounds, usage/truncation, credential isolation,
classification, opt-in and idempotency. API contracts reference the official
[chat API](https://docs.ollama.com/api/chat) and
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

Local smoke verification used the installed example model and synthetic CodeQL evidence.
After wire-schema compatibility adjustment, Ollama returned structured JSON with 1865
input and 637 output tokens. Its claims were rejected by the evidence gate and disposition
remained abstain. No model download or paid cloud request was made. The initial grammar
failure remains recorded separately as an unknown invocation with zero configured cost.
