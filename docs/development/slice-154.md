# Slice 154 — Full OSV export on linux/amd64

Ran the three-ecosystem export, including npm, against the amd64 image, completing the coverage
Slice 153 left at Go and Maven. `scripts/validate_osv_acquisition.py` gained a `--timeout` option,
because an emulated run needs a far longer budget than the 1,800 second default, and now records
per-stage wall time.

The run acquired 245,374 records with 79 shared advisories deduplicated and 430.5 MB expanded,
then loaded and indexed them with `--network none`: 244,439 records over 229,555 packages, with
935 withdrawn advisories excluded. Acquisition took 238.2 seconds and the offline load 212.3
seconds under emulation, against roughly 50 seconds for the same offline load natively.

The `inventory_sha256` differed from the arm64 run, and the cause was determined rather than
assumed. Of 245,373 records common to both exports, **245,372 are byte-identical**. One record,
`MAL-2026-16248`, differs only in its `modified` timestamp — 08:45 against 18:45 the same day —
and one advisory, `GHSA-vrf4-mx87-p53w`, was published upstream between the runs. There are
**zero architecture-attributable differences**; the digest difference is entirely upstream drift,
which is the behaviour the receipt's freshness limitation already states and which this run
evidences concretely.

That distinction matters because the inventory digest binds an export to the matching that
consumes it. Two exports taken minutes apart will not share a digest, and an operator comparing
digests across machines is comparing acquisition times, not architectures. Pin with
`--expected-sha256` where a reproducible input is required.

**This remains emulation, not native amd64 hardware.** The timings above are emulated and are not
a native performance figure; no native amd64 measurement is claimed. `ocp_qualified` stays false,
and OCP admission, SCC, storage, network and registry acceptance are untouched. No application
code changed and the suite is unaffected at 1,279 tests. `containers/osv-acquisition-image.json`
now records both images, both full-export runs and the cross-architecture comparison.

Next: native amd64 execution and the OCP acceptance items, both cluster environment work.
