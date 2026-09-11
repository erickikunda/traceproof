# Slice 113 — Current application in all smoke toolchain variants

Refreshed general, repaired-C# and Rust smoke image recipes install the current built wheel
and hash-locked Python dependencies over their existing digest-pinned toolchain bases.
Each build checks dependency consistency with pip check and records wheel/requirements
SHA-256 values in application-inputs.sha256. Non-root runtime settings and language-specific
allowlists/tool paths remain intact. No target build hooks or runtime network are introduced.

The batch rehearsal now has an explicit --provenance mode. It generates synthetic bounded
receipts for fixture archives; valid reports must show projection 13, snapshot_bound state,
expected commit/archive identity and unauthenticated remote history. The mixed batch includes
a tampered receipt which must be rejected while the later valid row still scans. The existing
plain mode checks missing-archive behavior and null provenance on ordinary archive reports.

Both modes run against C, C# and Rust images. These exercise the three runtime/toolchain
variants, not every language feature or live bank infrastructure. This is intake/report
portability; it does not qualify new CWE models or live LLM behavior. Current upstream
application tests remain the 1,003-test baseline from Slice 112; no application code changed
here. Native validation and build identities are recorded below.

The new containers/ocp-smoke-images.json inventory records the tested artifact identities
and common application inputs. It is not a full SBOM, signature or enterprise approval.
Building requires uv build first; Docker copies the existing wheel rather than interpreting
the working tree. Older image digests remain old snapshots even when a local tag moves.

No migration, registry push, cluster apply or model calls. Actual OCP/AMD64/PVC/network
qualification and representative bank quality/performance remain open. Next bounded Git-URL
CSV acquisition using the reserved repositories.csv convention and existing acquisition path;
keep that networked stage separate from offline archives.csv scanning.

Final results: 24 native scans across twelve batch scenarios pass. All three images pass
plain archive and synthetic-receipt modes; missing/tampered rows remain explicit while
later valid rows export reports. Zero model calls. Each build passes pip check. Lint,
formatting and whitespace checks pass; no application changes required rerunning the
previous 1,003-test regression baseline. All three installed input-hash records match the
local wheel and requirements.lock. See containers/ocp-smoke-images.json for exact digests.
