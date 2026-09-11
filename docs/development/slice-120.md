# Slice 120 — Optional live GCS reader and CLI

Adds google-cloud-storage as an optional gcs dependency and acquire-gcs with explicit ADC
opt-in. Reader creation is lazy after archive admission; metadata/range requests pin the
object generation and use preconditions, raw bytes, bounded timeouts and no storage retries.
The existing archive service verifies size/digest and removes failed output. No cloud call,
credential login, migration, model invocation or image build was performed.

Eight GCS tests pass, including mocked SDK range/precondition propagation, CLI credential
opt-in, sanitized SDK failure and prior archive contracts. Installed SDK signatures verified.
The base dependency set stays separate from the optional acquisition extra. Existing images
remain unchanged. See the GCS operator guide for ADC, memory/deadline and provenance limits.
Next durable GCS report provenance, then acquisition image packaging/validation.
