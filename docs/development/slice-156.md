# Slice 156 — Maven range-only advisories end to end

Slice 155 left the Maven `ECOSYSTEM` range path unexercised outside unit tests, because every
Maven advisory that matched there carried an explicit version list. This slice closes that gap
against the live export.

The acquired database holds 1,660 Maven affected entries that carry an `ECOSYSTEM` range and no
version list. Of those, sixty describe a range where a lexical comparison would miss a real
advisory, and eighteen where it would report one that does not apply. Two were taken as fixtures:

- `org.xwiki.platform:xwiki-platform-administration-ui` under GHSA-9j36-3cp4-rh4j, range
  `[4.2-milestone-1, 13.10.11)`. Version `13.10.1` is affected, but lexically `"13.10.1"` sorts
  below `"4.2-milestone-1"`, so a string comparison rejects it on the lower bound and **misses**
  it. The bound also carries a qualifier, so the case exercises numeric segments and
  `ComparableVersion` qualifier handling together.
- `org.apache.tomcat:tomcat` under GHSA-6m48-jxwx-76q7, range `[6.0.21, 6.0.37)`. Version `6.0.3`
  is **not** affected, but lexically `"6.0.3"` sorts above `"6.0.21"` and below `"6.0.37"`, so a
  string comparison reports a vulnerability the build does not have.

A synthetic repository declaring both was taken through intake and scanned against the live
database. It produced eighty candidates, **all by `maven_range`**, with no evaluation gaps and
both components fully evaluated. `13.10.1` matched GHSA-9j36-3cp4-rh4j and `6.0.3` did not match
GHSA-6m48-jxwx-76q7, which is the behaviour Maven ordering exists to produce. All candidates
remained `in_triage`.

Four regression tests carry those real range bounds, each declaring whether a lexical comparison
diverges there. The fixed-boundary and in-range controls are cases where lexical and Maven ordering
agree, and the test asserts that agreement rather than claiming divergence everywhere — an earlier
draft asserted divergence for all four and was wrong for the two controls. The changed files pass
lint and formatting against an unchanged repository-wide baseline, and the full suite passes: 1,286
tests.

**Range coverage is now demonstrated, not exploitability.** A match by `maven_range` means a
declared version falls inside an advisory's range and nothing more. The counts above come from
one live export and will drift. Both fixture coordinates are real published artifacts used as
range fixtures; no assessment of those projects is implied.

Next: native amd64 execution and the OCP acceptance items, both cluster environment work.
