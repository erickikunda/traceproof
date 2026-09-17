# Slice 146 — Maven version ordering for OSV ranges

Added `maven_version.py`, a faithful port of Maven's `ComparableVersion`, and bound it to
`ECOSYSTEM`-typed OSV ranges on Maven packages. Maven components that previously fell to
`partially_evaluated` because no ordering existed are now evaluated, which is the common shape
of GHSA-derived Maven advisories.

The port implements the algorithm rather than an approximation of it: qualifier ordering with
`alpha`, `beta`, `milestone`, `rc`, `snapshot`, release and `sp`; the `ga`/`final`/`release` and
`cr` aliases; single-letter `a`/`b`/`m` shorthand before a digit; trailing-padding normalization
so `1`, `1.0` and `1.0.0-ga` compare equal; and the rule that integers outrank qualifiers, which
outrank nested lists. Unknown qualifiers sort after every known one by name.

Slice 145 withheld this ordering on the grounds that an approximation would make wrong statements
about vulnerabilities. That standard is met rather than relaxed: the implementation is validated
against the ordering and equivalence vectors from Maven's own `ComparableVersionTest`, including
the twenty-value qualifier sequence, the twenty-five-value number sequence and twenty-two
equivalence pairs.

An ordering is bound to a range type and an ecosystem, never inferred from how a version string
happens to look. A `SEMVER`-typed range over `5.3.9.RELEASE` is still refused and counted, and an
`ECOSYSTEM` range on npm remains a gap because no npm ecosystem ordering is implemented. Gap
labels are now ecosystem-qualified (`range_type_ECOSYSTEM_npm`), which names what was skipped and
where.

Thirty-eight new tests: thirty over the ordering itself, and eight over matching, including six
Maven `ECOSYSTEM` range bounds, npm exclusion from Maven ordering, and a case that a lexical
comparison would get wrong — `5.3.10` against a range fixed at `5.3.9` must not match. The changed
files pass lint and formatting against an unchanged repository-wide baseline, and the full suite
passes: 1,166 tests. No migration and no schema change.

**Ordering fixes range evaluation, not missing versions.** A Maven repository whose versions come
from parent POMs is still largely `not_evaluated`, because inheritance is still never resolved. A
match remains a candidate establishing no reachability, no call path and no evidence that
vulnerable code is used or deployed. Only components reported `evaluated_no_match` support any
negative statement.

Next: networked OSV database acquisition in the acquisition container, which is the remaining
half of tier 3. Reachability, for which the existing call index is the input, remains
unimplemented and unassumed.
