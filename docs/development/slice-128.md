# Slice 128 — Python/Flask path candidates

Adds python-flask-path-v1 and rule traceproof/joern-python-flask-path-v1 for CWE-22 candidates.
Reuses isolated Flask source syntax selection and adds conservative unshadowed builtin open
read-path endpoints. Query matching retains file/line uniqueness and native flow evidence.
Existing command-injection selection is unchanged. No new advisory policy is enabled.

Fixtures: vulnerable, constant-path fixed, cross-file helper, disconnected source/sink,
shadowed open, and guard-present uncertain. Expected counts 1/0/1/0/0/1. The candidate
represents input-to-path flow, not independently established directory escape or exploit.
Report projection 15 adds explicit cwe_scope and CSV discovery_profile; unspecified older
profiles remain empty/unknown rather than inferred safe. Historical reports stay immutable.

Validation uses the existing pinned general Linux toolchain with current wheel installed
in isolated scratch, UID 1000710000, network none, read-only root, dropped capabilities and
bounded CPU/memory/PIDs. No image refresh, cloud, model call or migration. Native runner
exports readable reports and verifies profile/CWE data in JSON/HTML/scan-CSV. Results are in
work/slice128-reports/validation.json; full test log is work/slice128-full-tests.log.

All six native cases passed; full regression suite: 1,040 passed, one existing duplicate-ZIP
warning. Focused parser/advisory/workflow suite: 48 passed.

Next Slice 129: Java/Spring path candidates, subject to native Path/Files propagation checks.
Do not add general sanitizer or runtime reachability claims to make a fixture pass.
