# Slice 13: Anthropic Messages adapter

This slice adds an explicitly selected second live provider to bounded candidate triage. It does not implement automatic escalation or establish detection quality. Migration 0006 remains current.

## Operator configuration

Use the existing `traceproof triage` command with a JSON model configuration. Set `provider` to `anthropic`, `model` to an approved model identifier, `endpoint` to the approved HTTPS Messages endpoint, and `allowed_endpoint_hosts` to its exact hostname. Explicitly set `api_key_env` to `TRACEPROOF_ANTHROPIC_API_KEY` (the backward-compatible default remains the OpenAI variable). Supply that environment variable outside the configuration file. Set approved classifications, nonzero operator-supplied pricing, and `allow_source_transmission: true` only when transmission is authorized. No live model or tariff is selected by this slice.

The adapter uses Messages authentication and `output_config.format` JSON schema. Wire schema bounds are expressed in descriptions; the original strict local Decision model enforces them on receipt. Only a single text block from a completed assistant message is accepted. Refusal and truncation abstain; unexpected blocks never execute tools.

Both providers share the isolated HTTPS subprocess, total timeout, response cap, TLS verification, redirect rejection and disabled inherited proxies. Neither retries nor switches providers. Classification checks, durable budget reservation, idempotency and evidence validation remain common pipeline controls. Reports retain provider identity through the existing triage record.

No prompt cache is requested. If a response reports cache tokens, usage is marked unknown because this slice has no cache tariff configuration; the existing ledger retains the full reservation. This is conservative accounting, not invoice reconciliation or a guarantee that an upstream gateway cannot charge more. Operators must configure appropriate pricing and gateway limits.

## Validation and remaining work

Offline contract tests cover the request shape, strict local limits, completion/refusal/truncation, unexpected tool content, malformed usage, cache accounting, authentication headers, host policy and transmission opt-in. Existing pipeline and OpenAI tests exercise the shared controls. No paid requests or bank source transmissions are used.

Actual approved model/gateway compatibility, enterprise authentication, retention policy, cache pricing, independent reviewer escalation and distributed throughput remain future integration work. This adapter alone does not demonstrate 1,000 repositories/day or improve measured recall.

API references checked September 9, 2026: [Messages API](https://platform.claude.com/docs/en/api/messages/create) and [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
