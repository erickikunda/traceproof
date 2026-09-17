# Slice 152 — Opt-in OSV index caching

Added `--cache` and `--refresh-cache` to `get-osv` and `get-sbom`. A cache holds a derived index
under `<state-dir>/osv-cache/`, keyed by the profile's own digest, carrying only the fields
matching reads — advisory identity, aliases, summary, severity, affected versions, ranges and Go
ecosystem data. Record details, references and credits are dropped, so a 431 MiB export produces
a 56 MiB cache.

Measured against the qualified three-ecosystem export: 52.8 seconds with no cache, 71.9 seconds
on the first `--cache` run because it both verifies and writes, and 10.5 seconds on a hit. The
cached index was asserted identical to a freshly built one across all 229,554 packages.

**The saving is the integrity check, and that is the whole tradeoff.** The uncached path re-hashes
all 245,373 record files to prove the database still matches the `inventory_sha256` its profile
pins. A cache hit skips that and serves what was recorded when the cache was written, so a record
modified afterwards is not detected — the uncached path refuses that database outright. Caching is
therefore opt-in rather than default, and a test asserts the undetected case directly instead of
leaving it as an implicit consequence.

Every document names which path ran in `traceproof:osv_database_verification`: `reverified` when
every record was re-hashed this run, `cached` when a derived index was reused. `--refresh-cache`
forces verification and rewrites.

`load_profile` was split so the cheap profile parse is separable from the expensive inventory
verification, and `match_components` now consumes a prepared database rather than loading one
itself. A cache is accepted only when it names the same `inventory_sha256` and record count the
profile pins, so a different or updated export rebuilds automatically. Corrupt, truncated,
symlinked and schema-mismatched caches are ignored in favour of a verified rebuild, and a cache
that cannot be written never fails the scan, because an optimisation must not break a scan.

Fourteen new tests cover opt-in behaviour, index equivalence with a rebuild, identical candidates
and analysis state across cold and warm runs, invalidation by a changed export, rejection of a cache
naming a different inventory, four unusable cache shapes, refresh, symlink refusal, unwritable
caches, tamper detection on the uncached path, and the undetected-tamper case on the cached path.
The changed files pass lint and formatting against an unchanged repository-wide baseline, and the
full suite passes: 1,279 tests. No migration and no schema change.

**A cache changes performance, never candidates.** It establishes nothing about vulnerabilities,
does not alter matching, and leaves the CycloneDX analysis state at `in_triage`. It is local
derived state carrying the same trust as the database directory itself; where that trust is what
an operator wants to test, `--refresh-cache` or no cache at all is the correct setting. The
measured figures come from one live export on linux/arm64 and are not a fixed benchmark.

Next: nothing in the SBOM/OSV chain is outstanding except OCP, registry and AMD64 acceptance for
the acquisition image, which remain environment work rather than code.
