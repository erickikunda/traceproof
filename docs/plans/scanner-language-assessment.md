# Joern language assessment register

Language evidence baseline at Slice 105; see [Slice 127 CWE roadmap](cwe-coverage-roadmap.md) for current detection priorities. Results are scoped experiments, not language-wide production ratings.
CodeQL remains the reference POC backend. The main scan-run/scan-import workflow now
routes bounded Joern profiles explicitly; detection/triage qualification remains scoped.

| Target | Current evidence | Gate status / next work |
|---|---|---|
| Java/Spring | Bounded GET/String/JDBC model; cross-file positive/safe cases; nine restricted Linux cases including parse failures | Bounded discovery and explicit Spring advisory work (Slices 96–98); broad coverage and diagnostics remain unqualified |
| C#/ASP.NET | Experimental patch passes original ten cases plus ten bounded binding/flow checks; 18 baseline nodes span-validated with bounded syntax facts; 22-case restricted Linux run including durable discovery passed | Bounded Linux qualification passed; explicit bounded advisory added (Slice 101); broader HTTP source selection, semantics and bank OCP gates open |
| Rust | Cargo-based single-file and three-file pairs 1/0; returned snippets match lines in sample | Durable profile plus environment-to-shell expansion; nine additional restricted UBI 10 Linux cases pass; explicit bounded environment advisory added (Slice 103); attacker control, execution, broader Cargo/frameworks and qualified triage remain open |
| Python | Single-file and three-file pairs 1/0; disconnected case 0; sample source coordinates match | Durable integration plus opt-in Flask args/form.get-to-system profile; eight additional Linux cases pass; explicit bounded Flask advisory now accepted (Slice 99), with runtime identity and qualified triage still unproven |
| JavaScript/TypeScript | Each: single-file and ES-module three-file pairs 1/0; disconnected 0; sample source lines match | Durable integration plus opt-in Express profile: eight additional Linux cases per language pass; explicit bounded Express advisory accepted (Slice 100); factory import aliases, mixed-language/module variants and qualified triage remain open |
| Go | Single-file and three-package pairs 1/0; disconnected 0; sample source lines match | Durable integration plus opt-in HTTP form-to-shell profile; nine additional Linux cases pass; explicit bounded Go HTTP advisory added (Slice 102); execution/route reachability, advanced semantics and qualified triage remain open |
| C/C++ | Each: single-file and shared-header three-file pairs 1/0; disconnected 0; sample source lines match | Durable integration plus argv-to-system profile; eight additional Linux cases per language pass; explicit bounded argv advisory added (Slice 104); unresolved C++ identity, broader features, memory safety and qualified triage remain open |

All rows have bounded discovery and explicit advisory evidence. Next deliver the OCP-2
local smoke deployment bundle, as recorded in [the readiness checkpoint](../development/slice-105.md).
Do not equate these profiles with complete framework/CWE coverage or production qualification.
The following dated notes preserve historical decisions; their next-step statements are superseded.

C# alternative check (Slice 76): Opengrep stable/interfile alpha detect the three single-file
pairs but miss both cross-file variants and the combined-file positive. Neither qualifies
as the CodeQL evidence replacement. Continue bounded Joern repair; keep separate coverage
claims for any future supplementary Opengrep integration.


Slice 96 Java/Spring review gate: fresh native/query/SARIF/source provenance plus bounded
quoted syntax and path checks support explicit needs_review evidence assessment. Seven
restricted Linux cases pass; automatic Joern triage remains disabled. This does not
qualify runtime identity, semantic reachability, negative verdicts or benchmark recall.


Slice 97: the explicit Java/Spring policy is available in budgeted triage operations,
validated with replay and native preflight. Default scan execution still does not invoke
models; live quality, other language policies and runtime/recall claims remain unqualified.


Slice 98: Java/Spring main scans can explicitly request one bounded advisory page with
preconfigured budgets. Replay end-to-end acceptance passed. Discovery remains the default;
other language policies and live-model quality are not promoted by this result.


Slice 99 Python/Flask advisory: explicit joern-flask-review-v1 requires the opt-in
python-flask-system-v1 profile. Eight restricted Linux cases pass with three replay
needs_review advisories, zero live calls. Native generated intermediates are observations;
source and sink arguments are bound to isolated full-context AST endpoints and full-call
quotes. Budgeted scan/triage/report workflow is available; false-positive dismissal, safety
and semantic reachability remain unsupported. Next bounded Express JS/TS advisory.


Slice 100 Express advisory: joern-javascript-express-review-v1 and
joern-typescript-express-review-v1 explicitly enable bounded needs_review advice for the
express-request-eval-v1 profile. Native/query/SARIF/source and isolated syntax checks are
required; all native nodes must be literal on recorded lines. Eight restricted Linux cases
per language pass, six replay advisories total, zero live calls. No negative verdicts or
semantic reachability proof. Next reuse bounded C# repair evidence for advisory portability.


Slice 101 C#/ASP.NET advisory: the explicit joern-csharp-review-v1 policy replays the
existing repaired frontend's source mapping before advisory. Recognized Core FromQuery or
classic HttpGet syntax, mapped endpoint facts and complete context are required. It does
not broaden Lookup(name)-to-CommandText discovery or authenticate sink/framework APIs.
Four positive fixture families qualify for replay advice; foreign/unbound source candidates
remain visible but abstain without calls. Broader HTTP discovery, semantics and OCP gates
remain open. Next bounded Go HTTP-to-shell advisory.


Slice 102 Go HTTP advisory: explicit joern-go-http-review-v1 requires the go-http-shell-v1
profile, matching native/source evidence and isolated request/shell syntax. Nine restricted
Linux cases pass with three replay advisories, zero live calls. Ordinary process arguments,
unsupported imports/context and misleading endpoints do not qualify. Command construction
is not proof of execution or exposed routes; safety/negative verdicts remain unsupported.
Next Rust environment-to-shell advisory and C-family portability.


Slice 103 Rust advisory: joern-rust-env-review-v1 explicitly gates the rust-env-shell-v1
profile through isolated endpoint syntax and complete native/source evidence. The observed
eight-node cross-file path is retained rather than truncated. Nine restricted Linux cases
pass with three replay advisories, zero live calls. Environment attacker control, process
execution, broader Cargo/macros/conditional semantics and negative dismissal remain unproven
or unsupported. Next C/C++ argv-to-system advisory portability.
