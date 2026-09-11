# Slice 117 — Exact-repository private HTTPS credentials

Adds --credential-file to single and batch acquisition. Bounded JSON provides URL,
username and password; exact repository matching precedes output creation. Host allowlists,
TLS verification, no redirects and disabled inherited Git configuration remain enforced.
Only fetch receives a URL-scoped Authorization header through Git environment configuration.
Secrets are not persisted to Git config, source artifacts or acquisition reports.

Five new tests cover malformed secret data, pre-output repository mismatch, and native
local HTTPS fetch with accepted/rejected credentials and trusted/untrusted CA. The native
fixture exercises static Git HTTP transport at a test-only random port; it does not qualify
bank smart-HTTP, corporate proxies, OCP or end-to-end private acquire-git shallow fetch.

No migration or model calls. Existing images are unchanged. Next refresh the acquisition
image and exercise packaged transport/auth behavior; enterprise acceptance remains pending.
See the private-authentication guide for secret-mount and process-environment boundaries.
