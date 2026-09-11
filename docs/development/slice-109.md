# Slice 109 — Bounded public HTTPS Git acquisition

Added acquire-git as an explicit intake-preparation command. It accepts a credential-free
HTTPS URL on an operator-supplied exact hostname allowlist and either a full branch/tag ref
or a 40-character commit. A fresh bare repository performs a depth-one fetch; FETCH_HEAD is
peeled to a commit and recorded. An explicitly requested commit must match. Successful
output contains source.zip, input.csv with archive SHA-256, and acquisition.json with URL,
requested/resolved revision, Git version and per-file blob IDs/content digests.

The existing PVC archive intake consumes the generated CSV. No IntakeSpec/database migration,
scanner routing change, automatic scan or model call is introduced. Git provenance is a
sidecar associated by archive hash; current scan reports do not embed it. Consumers must
wait for successful command completion and state=acquired, retain the sidecar, and use a
fresh directory per acquisition. Reacquiring a moving branch is explicit new work.

## Security and completeness boundaries

No checkout, build, submodule recursion, LFS download or credential helper is used. Fresh
repositories, disabled hooks/templates, a minimal environment and ignored global/system Git
config isolate acquisition from inherited executable config. Only HTTPS transport is allowed;
redirects are disabled and TLS verification is enabled. No inherited proxy/CA/credential
configuration is copied. A trusted patched Git binary and OS networking policy are required.
The hostname allowlist is not DNS/IP isolation: approved egress controls must enforce actual
network destinations, including enterprise private ranges. No cloud/service deployment of
this network-bearing acquisition stage is included.

Source export uses ls-tree and cat-file raw blobs. It does not use git archive or checkout,
so export-ignore/export-subst attributes and smudge filters cannot change the exported source.
Unsupported symlinks, gitlinks/submodules, LFS pointers, path collisions and oversized files
fail the entire acquisition instead of creating a partial scan input. No omitted-content
success is claimed. SHA-256-format Git repositories, private authentication, custom corporate
CA/proxy configuration and Git CSV batch dispatch remain future scope.

Limits: 2,000 source files, 5 MiB per blob, 100 MiB total source, 256 MiB monitored temporary
workspace, default 300-second overall Git command deadline (1–900 configurable). Each command
runs in a separate process group that is terminated on timeout or observed limit breach.
Workspace monitoring is a soft cap with possible overshoot, not an OS disk/memory quota.
Use resource-controlled acquisition execution before processing untrusted fleet workloads.
Per-blob subprocess export is intentionally simple; high-throughput optimization is unqualified.

Failures remove source.zip/input.csv and retain a sanitized error-type receipt when writable;
temporary Git objects are cleaned up. Forced termination may leave incomplete directories;
there is no resume/durability guarantee. Existing output is never overwritten. Receipt/source
exports should be retained together. This is source acquisition, not signature verification,
repository-owner authentication or vulnerability coverage.

## Validation

Real Git fixture tests cover raw export despite export-ignore/filter attributes, commit
resolution after a branch changes, existing archive-intake handoff, no overwrite, unsupported
content rejection, environment isolation, CLI host rejection and bounded process execution.
Test-only fetch substitution uses a local fixture repository; production transport stays HTTPS.

A separate real public HTTPS acquisition of github.com/octocat/Hello-World.git succeeded at
commit 7fd1a60b01f91b314f59955a4e4d4e80d8edf11d, with one 13-byte README. Artifacts are under
work/slice109-public-git. This checks public transport and pinning only, not scan quality or
bank gateway compatibility. No repository was modified remotely and no credentials were used.

Git configuration behavior is based on [official Git configuration documentation](https://git-scm.com/docs/git-config).
The code disables hooks, inherited configuration, helpers and redirects explicitly rather
than relying on workstation defaults.

Next: bind acquisition provenance durably into intake/report contracts, then evaluate Git
CSV batch integration and bank-approved credential/CA/proxy configuration. Keep networked
acquisition separate from the existing offline scanner Jobs. GCS and bank/OCP/quality/fleet
acceptance remain open.

Final validation: 986 tests pass, with one existing duplicate-ZIP fixture warning; 17 new
acquisition tests are included. Ruff, formatting, whitespace and package build checks pass.
The initial submodule negative fixture mistakenly removed its gitlink before committing;
the corrected fixture now verifies rejection and passes in the final full suite.
