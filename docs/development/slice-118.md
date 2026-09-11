# Slice 118 — Packaged private HTTPS acquisition acceptance

Rebuilt the dedicated acquisition image from the current wheel with CA/proxy/credential
options. Verified installed wheel and dependency-lock hashes against build inputs and
retained Git/CA package inventory. Image identity is in containers/git-acquisition-image.json.

scripts/validate_git_private_container.py runs inside the image, using synthetic source,
a locally generated CA/certificate, a loopback HTTPS Git smart-HTTP server on port 443,
and an HTTP CONNECT proxy. It invokes the public single and CSV acquisition commands.
Correct credentials/CA pass shallow fetch; wrong password, wrong repository URL and
untrusted CA fail. The explicit proxy path records three CONNECT requests and succeeds.
The successful acquisition artifacts and CLI output are checked for credential/header leaks.
All server keys and fixture credentials are synthetic and remain in disposable scratch.

Runtime: Linux ARM64, UID 1000710000:0, read-only root, dropped capabilities, no privilege
escalation, 2 CPU/2 GiB/256 PID caps and bounded scratch. Network none preserves loopback
while preventing external access. Port 443 binding under this Docker configuration does
not imply a bank SCC permits fixture servers; deployed acquisition needs no listening port.

Also reran the public Git-to-offline-C-scanner handoff: rejected acquisition row retained,
one snapshot-bound report exported, zero candidates with incomplete coverage, zero model
calls. This proves handoff compatibility, not benchmark quality or production throughput.

No application code changes, migration, image push or OCP apply. Packaging checks, native
acceptance and Ruff passed. The previous 42 targeted application tests remain the baseline;
no unrelated test rerun. HTTPS-proxy TLS, authenticated proxies, SSO/token refresh and bank
infrastructure remain outside this acceptance. Next implement the remaining GCS archive
intake adapter with explicit source identity and offline handoff, beginning with local tests.
