# Separate networked acquisition container (Slice 115)

containers/Containerfile.git-acquisition packages the current application on the existing
digest-pinned UBI 9 Python image. That base already contains Git and CA certificates. It
installs hash-locked Python dependencies and a built wheel, checks dependency consistency,
and records Git/CA package versions plus wheel/requirements hashes. It does not include
Joern, CodeQL, JDK or Rust scanner toolchains. No credentials are built into the image.
The shared Python application still contains its normal modules; image separation is not
an authorization boundary preventing an operator from overriding the entrypoint.

```sh
uv build
docker build -f containers/Containerfile.git-acquisition -t veriflow:git-acquisition-linux-poc .
uv run python scripts/validate_acquisition_handoff.py \
  --acquisition-image veriflow:git-acquisition-linux-poc \
  --scanner-image veriflow:ocp-smoke-linux-poc work/acquisition-handoff
```

Use a fresh output directory. The rehearsal fetches the public zserge/jsmn repository and
rejects an unapproved-host row. The branch resolves to an exact commit in the receipt.
This depends on public GitHub availability and repository contents; it is not an immutable
quality benchmark. It scans the successful subset with the bounded C argv/system profile.
Zero candidates does not establish security coverage. Existing synthetic fixtures remain
the positive/negative scanner acceptance basis.

## Mount and stage contract

Acquisition reads /input/repositories.csv (read-only) and writes /handoff/batch. Its entrypoint
is `veriflow acquire-git-csv`; positional manifest/output arguments and --allowed-host are
explicitly supplied. The same CSV/host/ref/time/content limits apply as local acquisition.
For example, after setting up approved input and writable handoff mounts, the image arguments
are `/input/repositories.csv /handoff/batch --allowed-host github.com --max-rows 2 --timeout 300`.
Use a fresh batch subdirectory for each acquisition. No scanning starts in this stage.

Mount the *same handoff tree* at /handoff in the scanner container, read-only, and run the
batch scanner with `--input /handoff/batch`. This preserves absolute archive/receipt CSV
paths without rewriting or removing hash pins. The scanner gets separate writable /work,
/tmp and /reports mounts, with networking disabled. Input repositories.csv is not carried
into the offline handoff root. Receipt-enabled scanner images must be Slice 113 or newer.

The public acquisition rehearsal uses Docker bridge networking, restricted non-root UID,
read-only root, dropped capabilities, no privilege escalation and bounded resources. Its
Git hostname allowlist is an application check, **not network-level destination isolation**.
The scanner stage uses --network none and the existing runtime probe verifies external
network denial, UID, capabilities, writable paths and absent token/socket mounts.
The host directory permissions used for Docker Desktop are not bank PVC policy instructions.

The acquisition output can contain a successful archives.csv even when the command exits
1. Require terminal acquisition-batch.json, review every failed/unstarted row, and explicitly
decide whether to scan the success subset. Retain that summary with scan exports. A later
state=exported scan batch does not turn incomplete acquisition into complete processing of
the original repository list. The rehearsal deliberately verifies this distinction.

## Identity and operational limits

The tested artifacts are recorded in containers/git-acquisition-image.json. The application
input hash file and acquisition-packages.txt are inside /opt/veriflow. These are inventory
records, not a full SBOM, source signature or bank approval. Tags are mutable; use verified
image digests for handoff. Scanner and acquisition images may contain different application
builds while sharing the qualified receipt/CSV contract; the exact tested pairing is recorded.

No private authentication, custom corporate CA/proxy configuration or injected secrets are
introduced. Git still uses a minimal environment and ignores inherited credential helpers.
This stage is public HTTPS only. Do not embed tokens in URLs. The networked stage has not
been deployed to OCP and no permissive egress manifest is generated automatically. Bank
registry, namespace, network allow rules, storage/SELinux and auth integration remain open.

Runtime source fetching does not run checkout filters, hooks or target builds. Acquisition
contains network-capable Git and must be isolated according to enterprise policy; scanner
network denial does not retroactively protect the acquisition phase. Both phases require
scratch/handoff quotas; application byte monitoring can overshoot and does not enforce hard
OS limits. Forced termination can leave incomplete output; no distributed resume is claimed.
