# VeriFlow POC readiness checkpoint — Slice 105

**Assessment date:** 11 September 2026. **Code baseline:** completed Slice 104 working tree.
This checkpoint supersedes the next-step recommendations in Slice 95 and older language
assessment entries. It records implementation evidence, not production acceptance.

## Leadership view

The POC now has a CodeQL-independent, local scan-to-report path with optional bounded Joern
advisory for all nine explicit language selections. This is a meaningful functional
milestone. It is not yet a bank-ready deployment or broad vulnerability-coverage milestone.
The immediate next priority is the planned OCP-2 deployment bundle and local rehearsal.

We should stop adding depth to individual language gates for now. The remaining value is
in deployment, representative inputs, measured quality and operational integration.
No completion percentage is assigned: slice counts and passing fixture counts are not
comparable units of work, and the original percentage table predates the language expansion.

## Current language scope

All rows support explicit Joern selection, persisted report publication/retrieval and
bounded opt-in needs_review advisory. Native Linux fixture and replay evidence is recorded
in the linked slices. None supports an assertion of complete language/framework coverage,
automatic false-positive dismissal or proven runtime reachability.

| Language | Discovery profile | Explicit review policy | Candidate CWE scope | Evidence / principal limit |
|---|---|---|---|---|
| Java | default (Spring/JDBC) | joern-spring-review-v1 | CWE-89 | Slices 96–98; bounded GET/String/JDBC shapes |
| Python | python-flask-system-v1 | joern-flask-review-v1 | CWE-78 | Slice 99; bounded Flask args/form input to system |
| JavaScript | express-request-eval-v1 | joern-javascript-express-review-v1 | CWE-94 | Slice 100; bounded Express request to eval |
| TypeScript | express-request-eval-v1 | joern-typescript-express-review-v1 | CWE-94 | Slice 100; same bounded profile, distinct language selection |
| C# | default (repaired Lookup profile) | joern-csharp-review-v1 | CWE-89 | Slice 101; pinned repair; broader ASP.NET source discovery deferred |
| Go | go-http-shell-v1 | joern-go-http-review-v1 | CWE-78 | Slice 102; HTTP input to shell command construction, not execution proof |
| Rust | rust-env-shell-v1 | joern-rust-env-review-v1 | CWE-78 | Slice 103; restricted Cargo/toolchain; environment input is not proven attacker control |
| C | c-family-argv-system-v1 | joern-c-argv-review-v1 | CWE-78 | Slice 104; literal main argv indexing to direct system syntax |
| C++ | c-family-argv-system-v1 | joern-cpp-argv-review-v1 | CWE-78 | Slice 104; C-style subset, unresolved libc identity; no memory-safety coverage |

Default profiles for some languages are older feasibility models. Select the useful-input
profile shown above; enabling a provider alone does not widen discovery or evidence scope.
An unsupported evidence bundle remains visible and prevents the advisory call. Replay
acceptance validates orchestration, not live-model judgment. Reports remain incomplete.

## Requirement-to-evidence assessment

| Requirement | Current state | Remaining acceptance |
|---|---|---|
| CSV and local archive intake | Local admission, safe snapshots, durable single-worker processing | Git acquisition and GCS retrieval are not implemented; repository URLs alone do not fetch source |
| End-to-end local scans | Explicit CodeQL/Joern routing, source identity, candidate evidence, immutable reports | Representative dependency-bearing enterprise repositories and broader models |
| LLM-assisted review | Explicit policies, evidence preflight, budgets, replay, provider adapters including local Ollama | Live bank gateway compatibility, reviewer adjudication and measured quality/cost |
| Retrieve/share repository report | Python/CLI retrieval and JSON/HTML/CSV exports | Hosted HTTP API, authorization, pagination/service contracts and API operator guide |
| Ground-truth evaluation | Offline benchmark contracts and saved-report evaluation/comparison code | Supplied 50-repository corpus, frozen configuration and adjudicated quality run |
| Laptop Linux preparation | Restricted ARM64 container fixture acceptance and pinned toolchains | Unified deployment handoff, target architecture qualification, package/image approvals and SBOM |
| OCP dev execution | Required and explicitly deferred until functional completion | Namespace bundle, real SCC/SELinux/PVC/network acceptance and platform approval |
| Persistence/orchestration | SQLite and local worker locking support current POC | PostgreSQL contract/concurrency qualification; distributed coordination before multiple workers |
| 1,000 repositories/day | Design objective only | Representative workload, scheduling, backpressure, cost/latency measurements and failure recovery |

There is **no hosted HTTP API today**. Mentions of report APIs in slice notes refer to
Python interfaces unless explicitly marked as proposed HTTP routes. The system-design
retrieval routes are proposals. Do not send HTTP requests to them or treat generated
OpenAPI documentation as an existing deliverable. The API guide is due with the first
hosted API, as already required by the implementation plan.

Redis is not a current POC dependency. Introducing a single offline OCP smoke Job does not
require Redis. SQLite must not become a shared multiworker database on a PVC by implication.

## Next implementation slice: OCP-2 offline smoke deployment bundle

Deliver a namespace-scoped example using a pinned Joern image, a dedicated ServiceAccount,
no token automount, a bounded Job, explicit scratch and report volumes, and extraction egress
denial. Keep LLM credentials out of this stage. Use the existing single-worker Python/CLI
workflow and a supplied synthetic archive/CSV; export the exact JSON/HTML report to the
report mount. A first smoke Job may keep SQLite on ephemeral local storage, clearly labeled
as disposable with no restart-durability claim.

Validate manifest structure/configuration locally and rehearse its entrypoint under the
existing restricted Docker settings. Do not apply manifests to a cluster or push images.
Keep image registry/digest, namespace and PVC selection explicit for later bank substitution.
Do not pin a macOS-derived UID into an OCP namespace or request privileged/anyuid execution.
Document failure artifacts and the difference between a successful Job and a complete scan.

Acceptance: reproducible local archive-to-published-report rehearsal; bounded resources;
no embedded credentials; no external runtime network dependence; documented writable paths;
operator steps and honest deferred-cluster checks. This is a focused OCP-2 subset, not
completion of OCP-3 shared persistence or OCP-4 cluster acceptance.

## Follow-on priorities and bank handoff

1. Complete the offline deployment handoff above, then validate a representative local
   input and report workflow beyond tiny language fixtures.
2. Integrate available ground truth into a frozen benchmark run; select detection expansion
   from observed misses and false-positive adjudication rather than intuition. This requires
   the actual corpus and labels; no synthetic score should substitute for that evidence.
3. Qualify live provider/gateway behavior with bounded budgets when approved configuration
   is available. Keep offline extraction separate from credential-bearing triage.
4. Add PostgreSQL qualification and hosted-service contracts before distributed workers.
   Deliver the API operator guide with the actual API, not invented routes. Prioritize
   Git/GCS acquisition according to the agreed input source for the pilot.
5. Execute actual OCP dev acceptance on the bank's architecture/storage/network policies,
   followed by representative recovery and throughput testing before claiming fleet scale.

Later bank inputs: worker architecture, namespace/SCC constraints, approved registry and
package sources, PVC/storage policies, gateway/CA/egress requirements, representative source
archives and ground-truth labels. None is needed to prepare the next local smoke bundle.
Do not request keys or bank source in this personal environment without an approved process.

## Verification and traceability

Read against implementation-plan OCP-1–OCP-4, pipeline.py, intake.py, joern_claims.py,
evaluation.py, reports.py, containers and operator guides. The current regression baseline
is 947 passing tests from Slice 104, with one duplicate-ZIP fixture warning. This slice
changes documentation only; no new execution result, migration or runtime behavior is claimed.

The language policy register and assessment are now reconciled. Older chronological slice
notes remain historical; this checkpoint and the current matrix guide subsequent work.
