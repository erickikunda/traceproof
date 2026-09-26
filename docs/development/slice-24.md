# Slice 24: durable triage request limits

Migration 0008 adds a fixed request limit to each run's triage budget, independent of
monetary pricing. This bounds zero-cost local Ollama/replay work and durable ledger growth.

```bash
uv run veriflow init
uv run veriflow triage-budget RUN_ID 0 --max-requests 20
uv run veriflow triage-report RUN_ID
```

New budgets default to 100 requests unless explicitly configured (0–10000). Zero disables
new requests. Both money and request limits are fixed once created; omitting the option
when revisiting an existing budget preserves its configured value. Migration assigns
100 to existing budgets without deleting or modifying their recorded calls. Runs already
at or beyond that count cannot admit new requests, but historical keys remain retrievable.

Every distinct persisted triage request consumes one slot, including evidence/rule/budget
skips, refusals, invalid output and unknown/interrupted calls. This is a request limit,
not a claim about exact provider invocations. Validation failures before admission do not
consume a slot. Repeating an identical key returns the original result; conflicting keys
still fail. Once exhausted, a new key fails with a clear error before another record or
provider call is created. The local worker lock serializes admission; this is not yet a
distributed reservation implementation.

The triage ledger now exposes `max_requests` and `remaining_requests`; `total` retains
its existing meaning. Monetary reservations, source classification, opt-in, evidence
checks and immutable published reports are unchanged. No provider calls are needed to
test the cap. No automatic limit increase, refund or deletion bypass is supplied.

Tests cover zero-cost calls, retrieval at exhaustion, skipped requests, zero/invalid
limits, fixed budget behavior and repeatable migration preserving prior results.
The default operator database is not upgraded by tests; apply `init` for schema 0008
before using triage with the updated code.
