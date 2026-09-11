# Slice 123 — Consolidated intake and POC readiness

Documentation checkpoint after packaged Git/PVC/GCS delivery. The consolidated intake
operator guide identifies entry points, credentials, immutable handoff, failure accounting,
image compatibility and report retrieval. Removes superseded immediate-next-step entries
from the plan's current checkpoint; historical slice records remain intact.

## Remaining gates, in execution order

1. Refresh specialized C#/Rust images for projection 14 and test synthetic GCS handoff
   using existing bounded fixtures. This closes a real compatibility gap without widening
   language claims. Also exercise the other packaged general-language selections against
   the current application before promoting a unified image inventory.
2. Consolidate a repeatable local acceptance entrypoint/scorecard for current intake and
   image variants. Preserve tests' exact input/toolchain identity and zero-model default.
3. Representative quality: supplied 50-repository benchmark and adjudication when available
   in an authorized environment. Local plumbing can proceed without bank corpus access;
   fixture counts do not establish precision/recall or useful portfolio coverage.
4. Required bank OCP dev acceptance at functional POC completion: target architecture,
   registry/SCC/PVC/SELinux/network, cloud/Git identities, dependency access and approved
   model gateway. Docker preparation does not satisfy this gate. No need to install OCP
   locally or supply bank credentials on the personal laptop.
5. Pilot scale: PostgreSQL concurrency/recovery, scheduling/fairness, durable cost accounting,
   reporting authorization/API and measured throughput. Hosted API gets its operator guide
   when implemented. Redis remains optional ephemeral coordination, not durable truth.

Not complete: real GCS transport acceptance, private bank Git/SSO, HTTPS/authenticated proxy
acceptance, GCS warm-cache/retrieval-cost accounting, GCS batch acquisition, full SDK hard
resource isolation, broad CWEs/frameworks, or 1,000 repositories/day qualification. These are
tracked scope/acceptance items; no completion percentage is inferred from slice numbering.

No application/image/schema change or new scan/model call in this slice. Guide links and
CLI names/options checked against the repository. Prior 1,035-test suite and Slice 122
native packaging acceptance remain the baseline. Next: specialized image refresh.
