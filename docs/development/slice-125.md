# Slice 125 — General image GCS acceptance matrix

The GCS handoff validator now accepts all nine language selections using the existing
smoke fixture mapping. The general image runs Java, Python, JavaScript, TypeScript, Go,
C and C++ vulnerable/fixed pairs; C#/Rust acceptance from Slice 124 is retained with exact
image IDs. No language rule/model changes or additional evidence claims are introduced.

scripts/summarize_gcs_acceptance.py requires all 18 unique language/case results, expected
1/0 candidate counts, one acquisition image, consistent scanner image within each pair,
and zero cloud/model calls. It rejects incomplete/duplicate/mixed-pair inputs. The saved
matrix records exact image and report identities and result paths. This checks recorded
acceptance results, not authenticity of arbitrary operator-supplied JSON.

Each new run performs synthetic SDK acquisition, receipt-pinned archive capture, a real
bounded offline scan, runtime probe and projection 14 report checks. Coverage remains
incomplete even for the fixed fixture. No actual GCS, OCP or live LLM testing is claimed.
No migration, image rebuild, application change or commit in this slice. Ruff/diff checks
and native acceptance cover the changes; previous full application suite remains baseline.

Next functional work should strengthen operational completeness: a local acceptance/runbook
entrypoint with explicit required and externally deferred gates, then the remaining planned
POC integration work. Representative bank corpus/gateway/cloud/OCP access remains external;
fixture matrix completion does not qualify precision, recall or 1,000 repositories/day.
