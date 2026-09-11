# Slice 115 — Separate acquisition image and offline scanner handoff

Added a standalone acquisition container on digest-pinned UBI 9 Python/Git/CA userland.
It installs the current wheel/hash-locked Python dependencies, runs pip check and records
input/package identities. No scanner toolchains or credentials are copied. Acquisition runs
with explicit repositories.csv/output/host policy, separate from offline scanner execution.

The real two-container rehearsal acquires public zserge/jsmn and rejects an unapproved-host
row. The scanner reads the same absolute /handoff/batch paths read-only with --network none;
no CSV rewriting or receipt weakening occurs. It publishes a snapshot-bound report for the
successful subset while original acquisition remains incomplete. Runtime/network probes
pass for the offline scanner. The bounded C profile reports zero candidates; no clean or
quality/recall conclusion follows.

Validated public commit: 25647e692c7906b96ffd2b05ca54c097948e879c.
Acquisition image: sha256:a5f3337740b0134a66f56c18e5164ba0e1130db659a0f819928d96e2730764a7.
Scanner image: sha256:f5b26ceb13df5cf0c37043d9f04ebc0e86cd5134dbf4646aff3dc02dcdec2bc4.
Artifacts: work/slice115-handoff. Zero model calls, one real offline C scan. No cluster apply,
registry push, migration or private credentials. Public transport availability is external.

Package build, dependency consistency, lint, formatting and whitespace checks pass. No
application code changed; the 1,009-test application baseline remains from Slice 114.
Native packaging/handoff checks are the new validation evidence. The inventory is not a
complete SBOM or signed supply-chain attestation. Actual OCP/AMD64/storage/network approval
remains deferred.

Next: enterprise acquisition configuration for corporate CA/proxy and private repositories,
with explicit operator-controlled credential handling, no URL secrets and local validation
where possible. Live bank gateway access is a separate acceptance gate. GCS, representative
benchmark and production persistence/fleet qualification remain open.
