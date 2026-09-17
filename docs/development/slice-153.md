# Slice 153 — OSV acquisition image on linux/amd64

Built `containers/Containerfile.osv-acquisition` for linux/amd64 and re-ran the qualification
against it. Both images are now recorded in `containers/osv-acquisition-image.json`, which gains
a per-architecture shape.

Two build-time unknowns are retired. The pinned base digest is a manifest **list**, so it resolves
to a different manifest per architecture — `sha256:debc1c4a…` on amd64 against `sha256:5ccc2dee…`
on arm64 — and the digest therefore pins reproducibility within an architecture, not across them.
The amd64 manifest pulls and builds. `greenlet` is the only native-code dependency in
`containers/requirements.lock`; its x86_64 manylinux wheel installs under `--require-hashes
--only-binary=:all:`, imports at runtime, and `pip check` reports no broken requirements.

The qualification gates behave identically: an unallowed host is refused without creating an
output directory, unpinned acquisition requires the explicit opt-in, a wrong pinned digest is
refused, the real acquisition succeeds with every archive `observed_only` and zero model calls,
and the export then loads and indexes with `--network none`.

The same Go and Maven export acquired on both architectures produced a **byte-identical**
`inventory_sha256` of `2d34148a097fde07e7a3ccd6f61faeed1103826a33d0f63efc9652664045fc97`, the
same 16,363 records, the same 11 shared advisories deduplicated and the same 16,104 loaded with
259 withdrawn excluded. Cross-architecture determinism of the pinned inventory is therefore
observed rather than assumed, which matters because the inventory digest is what binds an export
to the matching that consumes it.

**The amd64 image was built and run under qemu emulation on an arm64 host, not on native amd64
hardware.** That retires the build-time and functional unknowns; it does not establish native
behaviour. No performance figures are claimed for amd64, because emulation makes them
meaningless. The three-ecosystem export including npm was qualified on arm64 only; the amd64 run
covered Go and Maven. `ocp_qualified` remains false, and OCP admission, SCC, storage, network and
registry acceptance are untouched by this slice. No application code changed and the test suite
is unaffected at 1,279 tests.

Next: native amd64 execution and the OCP acceptance items, both of which are cluster environment
work rather than code.
