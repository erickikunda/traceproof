# CWE coverage assessment and delivery roadmap — Slice 127

Assessed against the current repository after Slice 126. The priority is useful detection
breadth and functional completeness, not infrastructure refinement. SQLite/single-worker
remains the POC runtime. The assessment itself introduced no detector; Slice 128 subsequently implements the bounded Python/Flask CWE-22 profile described below.

## Original baseline at Slice 127

**At Slice 127, nine language selections covered bounded examples in three CWE families.**
Language/frontend support, a reachable data-flow path, advisory acceptance and a confirmed
vulnerability are different capabilities. No portfolio precision/recall has been measured.

| Language/framework | Joern discovery profile | CWE / selected source-to-sink pattern | Advisory status and missing scope |
|---|---|---|---|
| Java/Spring | default | CWE-89: public GetMapping String RequestParam to exact JDBC Statement.executeQuery(String) | Explicit Spring needs_review policy; other verbs/bindings, JDBC execution APIs, templates/ORMs and wrappers not generally covered |
| Python/Flask | python-flask-system-v1 | CWE-78: bounded request args/form.get to os.system | Explicit Flask needs_review; subprocess variants, other frameworks and general sanitizer semantics not covered |
| JavaScript/Express | express-request-eval-v1 | CWE-94: bounded request data to eval | Explicit JS needs_review; command execution, HTML sinks, SQL, templates and arbitrary module patterns not covered |
| TypeScript/Express | express-request-eval-v1 | CWE-94: bounded request data to eval | Separate TS needs_review; same principal gaps as JS, not universal TS binding |
| C#/ASP.NET | repaired default | CWE-89: experimental Lookup(name) source to CommandText assignment | Explicit bounded source-mapping advisory; real HTTP discovery remains narrower than framework support suggests |
| Go/net/http | go-http-shell-v1 | CWE-78: request form data to shell command construction | Explicit needs_review; command construction does not prove execution or route exposure |
| Rust | rust-env-shell-v1 | CWE-78: literal environment lookup to chained shell argument | Explicit needs_review; attacker control of environment and broader Cargo/macros unproven |
| C | c-family-argv-system-v1 | CWE-78: main argv indexing to system argument | Explicit needs_review; no broad memory-safety coverage |
| C++ | c-family-argv-system-v1 | CWE-78: bounded C-style argv/system pattern | Explicit needs_review; unresolved API identity and broad C++ semantics remain gaps |

All rows are candidate discovery, not whole-CWE qualification. Fixed-fixture zero results
are not evidence that arbitrary application guards work. Older lookup-based feasibility
profiles remain available for some languages but add neither a new CWE family nor general
HTTP source coverage. Automatic false-positive dismissal and runtime exploitability are
not qualified by these advisory policies.

Evidence: src/traceproof/queries/joern-*.sc, profile/rule selection in joern.py,
language-specific claim/parser modules, and the [language register](scanner-language-assessment.md).
The [readiness checkpoint](../development/slice-105.md) records policy names and fixture scope.
Slices 124–125 validate packaging/handoff for existing profiles; they do not widen detection.

CodeQL remains the reference backend where permitted. Trusted .ql/.qls input can yield
additional candidates, but the configured suite determines those checks and existing gates
do not automatically gain the corresponding triage semantics. This assessment does not
count every installed CodeQL query as validated TraceProof coverage. Opengrep is an assessed
potential supplement, not a currently integrated broad-coverage backend.

## Delivered expansion — Slice 128

Python/Flask python-flask-path-v1 adds CWE-22 input-to-open read-path candidates. Native
vulnerable/fixed, cross-file, disconnected, shadowed and guard-uncertain fixtures pass.
This is a fourth bounded CWE family, with discovery only and no qualified advisory or
proven directory escape. See [operator guide](../guides/python-path-discovery.md).

Slice 129 adds Java/Spring java-spring-file-path-v1 using exact Files.readAllBytes(Path)
selection and bounded Path.of propagation. It remains discovery-only; see the
[Java guide](../guides/java-path-discovery.md). Next SSRF, then SQL breadth.

Slice 130 adds Python/Flask python-flask-ssrf-v1, CWE-918, for bounded requests.get URL
flow. This is a fifth bounded CWE family; destination access and SSRF advisory remain
unverified/unsupported. See [SSRF guide](../guides/python-ssrf-discovery.md). Next SQL breadth.

Slice 131 adds Python/Flask python-flask-sql-v1 for immediate sqlite3.connect(...).execute
query text, with a parameterized negative. Cursor variables and other drivers remain gaps;
see [SQL guide](../guides/python-sql-discovery.md). Next deterministic profile selection.

## Selection rationale

Priorities below are engineering judgments based on the requested enterprise use cases
and reuse of working source/flow/report machinery. They are not a measured Wells Fargo CWE
frequency ranking. The supplied 50-repository labels are not available in this checkout;
when authorized labels become available, use them to revise the order and quantify misses.

| Priority | Gap | First target | Why now / principal evidence challenge |
|---|---|---|---|
| 1 | CWE-22 path traversal | Python/Flask, then Java/Spring | Adds a new weakness family using existing request models; must distinguish an attacker-controlled path from demonstrated escape of an intended directory |
| 2 | CWE-918 SSRF | Python/Flask, then Java/Spring | Models request data entering outbound URL APIs; URL control alone does not prove access to a forbidden destination or deployment egress |
| 3 | CWE-89 SQL injection breadth | Python DB-API and Java JDBC expansion | Adds common database paths and API breadth; parameterized value arguments must not be treated as SQL syntax |
| 4 | CWE-78 process execution breadth | JS/TS child_process, Java, C# | Cross-language reuse of a useful family; distinguish shell interpretation from ordinary argument passing |
| 5 | CWE-79 reflected XSS | Express and selected server rendering APIs | Requires response/output context and escaping semantics; a generic string flow is insufficient |
| Subsequent | CWE-502 deserialization, CWE-611 XML entities | Java and C# first | Constructor/options/type-specific behavior and runtime dependencies require scoped fixtures |
| Subsequent | CWE-862/863 authorization and CWE-639 object access | Selected web resource endpoints | Needs policy/tenant/ownership context; missing a familiar guard name is not a vulnerability proof |
| Separate bounded track | C/C++ memory safety (e.g. CWE-787/125/416) | Selected APIs/lifetime patterns | Requires bounds/lifetime/control evidence; argv/system acceptance provides no basis for memory-safety claims |

Secrets, dependency vulnerabilities and configuration checks remain other useful detection
lanes, but are not implicitly covered by these source-flow profiles. Do not advertise all
rows above as a committed implementation or defer every new family until all languages
have perfect parity.

## Immediate delivery sequence

1. **Slice 128 — Python/Flask file-path candidates (CWE-22).** Reuse qualified request-source
   selection; add narrowly recognized builtins.open path arguments with source-binding
   checks. Start with direct strings and bounded concatenation. Do not claim pathlib,
   framework file-serving helpers or safe canonicalization until fixtures support them.
   A tainted filename should be reported as a path-traversal candidate needing confinement
   evidence, not a proven directory escape. Explicit discovery profile; no automatic LLM calls.
2. **Slice 129 — Java/Spring file-path candidates (CWE-22).** Start with the existing public
   GetMapping/RequestParam source shapes and explicitly resolved java.nio.file APIs. Verify
   how Path.of/Paths.get propagation appears in the actual CPG before choosing sink signatures.
   If the frontend loses essential flow, report the gap and bound the model rather than
   adding unqualified all-string matching.
3. **Slice 130 — Bounded SSRF discovery (CWE-918).** Python request-to-requests.get URL first;
   Java portability is next if the same bounded slice remains manageable. Match URL argument
   position and imports; preserve unknown redirect, DNS, destination-policy and egress facts.
4. **Slice 131 — SQL discovery expansion (CWE-89).** Add Python DB-API query-text flow with
   parameter-binding negatives, or Java JDBC variants first if native feasibility/benchmark
   evidence favors them. Do not mistake a tainted bound value for dynamic SQL syntax.

These are bounded objectives, not promises that four slices complete every family. Adjust
scope when concrete scanner limitations emerge. Prefer a working additional detector with
truthful unsupported evidence over repeatedly polishing an already adequate detector.

## Common acceptance gate for each addition

- One explicit versioned profile/rule, deterministic selection and persisted engine/CWE identity.
  Existing default profiles retain their previous meaning; no silent rule expansion or automatic
  second scan. If multiple profiles are run, retain separate attempts and coverage obligations.
- A vulnerable/fixed pair, cross-file positive, disconnected source/sink negative, and a
  misleading API or shadowed binding case. The fixed pair initially uses a constant/explicit
  allowlisted selection or genuinely parameterized API, not a guessed sanitizer.
- A guard-present uncertain example: candidate remains reviewable or unsupported; do not
  suppress it merely because normalize/resolve/check functions appear nearby.
- Native Joern flow plus matching source coordinates, query identity and retained context.
  Query/source/parser failures must produce incomplete coverage, never a clean result.
- Durable scan-to-report retrieval, HTML/JSON/CSV agreement on CWE and profile, and one restricted
  Linux fixture run. Reuse the established runner; do not repeat all language packaging checks
  unless shared behavior changes.
- Initially discovery-only where the new evidence gate is absent. Clearly disclose advisory
  unsupported; do not force a CWE-22 or CWE-918 candidate through a CWE-78 policy. Add bounded
  advice only when evidence types support it, without weakening existing gates.
- Zero live model calls for engineering acceptance. Later evaluate fixed configurations against
  the authorized benchmark, count unsupported cases/misses, and adjudicate extra candidates
  before reporting precision. Preserve previously detected candidates in comparisons.

## Measuring progress honestly

Track the tuple (language, framework/source model, sink/API, CWE, profile version), with
separate statuses for native discovery, source evidence, advisory and benchmark results.
Count a newly qualified tuple as increased scope; do not use slice counts or language counts
as a recall percentage. Report query failures, omitted inputs and untriaged candidates.

A CPG reachableByFlows result describes modeled data movement. Joern documents that missing
external-method semantics can propagate taint broadly and introduce unrelated paths; query
models and counterexamples therefore remain necessary. [Joern data-flow steps](https://docs.joern.io/cpgql/data-flow-steps/),
[custom semantics](https://docs.joern.io/dataflow-semantics/).

CWE terminology references: [CWE-22](https://cwe.mitre.org/data/definitions/22.html),
[CWE-89](https://cwe.mitre.org/data/definitions/89.html),
[CWE-918](https://cwe.mitre.org/data/definitions/918.html). These classify weakness concepts;
they do not establish which APIs our implementation detects.

## Slice 133 — Java SSRF expansion

Java/Spring `java-spring-url-stream-v1` adds CWE-918 request-to-URL.openStream
receiver candidates and joins automatic selection. Five bounded CWE families remain;
this expands language/API scope, not the family count. See the
[guide](../guides/java-ssrf-discovery.md). Next prioritize process-execution breadth
in JS/TS, then reflected XSS, subject to native frontend evidence.

## Slice 134 — JavaScript/TypeScript command execution

`express-request-exec-v1` adds CWE-78 request-to-child_process.exec command text
for both languages. Automatic selection retains separate eval/exec reports. This
expands language/API breadth within the existing five CWE families; advisory is
unsupported. See [guide](../guides/express-command-discovery.md). Next reflected XSS.

## Slice 135 — explicit HTML reflected-XSS candidates

`express-html-send-v1` adds CWE-79 for JS/TS Express request fields to explicit HTML
response bodies. JSON and explicit plain-text output are outside this detector.
Six bounded CWE families now have discovery profiles; this is not complete CWE
coverage or measured recall. See [guide](../guides/express-html-discovery.md).
Next assess Java deserialization scope with native positive/negative fixtures.

## Slice 136 — Java deserialization candidates

`java-spring-object-read-v1` adds CWE-502 String request input to ObjectInputStream
readObject receiver. The initial constructor/Base64 flow remains discovery-only;
filter adequacy and gadget availability are not inferred. Seven bounded CWE families
now have discovery profiles; no claim of whole-CWE coverage or measured recall.
See [guide](../guides/java-deserialization-discovery.md). Next Java XML configuration
and external-entity candidate feasibility.
