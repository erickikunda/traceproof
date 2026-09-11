# Slice 127 — CWE coverage assessment

Inventoried current Joern query/profile selection and reviewed existing language/advisory
acceptance. Nine language selections currently cover bounded patterns in CWE-78, CWE-89
and CWE-94; broader CodeQL suites are operator-dependent and not equivalent to qualified
triage coverage. No new detection is introduced in this assessment.

The CWE roadmap separates implemented candidate scope from advisory, runtime and benchmark
claims. Next Slice 128 adds bounded Python/Flask file-path candidates, then Java/Spring
path candidates, SSRF and SQL breadth. Each addition must pass vulnerable/fixed, cross-file,
disconnected and misleading-binding fixtures, persist usable reports, and receive restricted
Linux validation. Unsupported advice remains explicit; no gate weakening for a new CWE.

This priority is based on engineering/enterprise relevance, not bank portfolio measurements.
Benchmark labels remain unavailable locally. PostgreSQL/distributed work stays deferred.
Documentation links and profile inventory checked; no source execution, image build, cloud
access, migration or model call. See ../plans/cwe-coverage-roadmap.md for scope and evidence.
