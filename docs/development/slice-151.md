# Slice 151 — OSV acquisition container qualification

Built and qualified `containers/Containerfile.osv-acquisition` against the live OSV export, and
rewrote `scripts/validate_osv_acquisition.py` as a host-side driver matching
`validate_acquisition_handoff.py` rather than a script running inside the container. It applies
the same hardened runtime as Git acquisition: read-only root, dropped capabilities, no new
privileges, bounded CPU, memory and PIDs, with `/work` and `/tmp` as tmpfs and the export a bind
mount.

Qualification found three limits that were wrong, all of which refused the real export:

- `MAX_RECORDS` was 50,000. The live npm export alone carries **229,010** advisories, and the
  three-ecosystem export carries 245,373. Raised to 500,000 in both the acquirer and the loader,
  with the archive and expanded byte caps left as the real backstop.
- `osv_database.load_profile` reused `csharp_dependencies.inventory`, whose `MAX_FILES` cap of
  20,000 is an order of magnitude below a real export. Replaced with a dedicated
  `record_inventory` that keeps the symlink refusal and carries the OSV limit.
- Together these meant a full export could be acquired but never loaded. Both are now exercised
  end to end.

Measured bounds that held: largest record 71.4 KiB against a 2 MiB cap, highest member
compression ratio 18.2 against a 200 cap, 431 MiB expanded against a 1 GiB cap, npm's 205 MiB
archive against a 256 MiB cap. No archive member was nested or a directory, so the flat-record
refusal did not trigger on real data. 935 withdrawn advisories were loaded, counted and excluded
from matching.

The container run validates that an unallowed host is refused without creating an output
directory, that unpinned acquisition requires the explicit opt-in, that a wrong pinned digest is
refused, that the real acquisition succeeds with every archive labelled `observed_only` and zero
model calls, and that the acquired export then loads and indexes with `--network none`. Both a
Go/Maven run and a full three-ecosystem run passed; the image identity and both reports are
recorded in `containers/osv-acquisition-image.json`.

Qualification also measured an operational cost that was previously unknown: a full three-ecosystem
export costs roughly 50 seconds and 1.7 GiB of peak RSS on **every** matching run, because the
profile is re-hashed and the index rebuilt each time. Go and Maven alone cost about 3 seconds and
120 MiB. The operator guide now carries the table and advises fetching only the ecosystems actually
scanned. The changed files pass lint and formatting against an unchanged repository-wide baseline,
and the full suite passes: 1,265 tests.

**Record counts reflect the live export at qualification time and are not a fixed acceptance
threshold.** Freshness is the moment of acquisition. Acquisition establishes no vulnerability
position and performs no matching. No OpenShift, registry push, AMD64 or bank network acceptance
is claimed, and `ocp_qualified` remains false. The image was built and run on linux/arm64 only.

Next: index caching or a prebuilt index would remove the per-run load cost that this
qualification exposed; nothing in the pipeline depends on it yet.
