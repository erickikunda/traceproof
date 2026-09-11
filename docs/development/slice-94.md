# Slice 94 — C/C++ command-line-to-system discovery

## Outcome

The opt-in c-family-argv-system-v1 profile extends C and the C-style C++ subset beyond
lookup(input) fixtures. Main scan-run/scan-import and both standalone language commands
accept the profile, preserving defaults. No migration, LLM key or source build is required.

Sources are positive decimal constant-index reads of global main's second character
pointer-vector parameter. Graph references link the indexed identifier to the parameter;
parameter spelling is unrestricted. Sinks require the unqualified system graph signature.
If a repository-defined method named system exists, all sinks are conservatively withheld.
Joern supplies the recorded dataflow; the adapter does not invent links.

Separate C/C++ rule identities, packaged query digests, report profile metadata and
profile-aware retry suppression preserve provenance. The existing report retrieval,
publication, source-coordinate checks and evidence gates apply. Benchmark coverage audits
recognize the new CWE-78 scopes without qualifying precision or recall.

## Acceptance

Eight cases per language: direct vulnerable/fixed (1/0), three-file/shared-header
vulnerable/fixed (1/0), renamed array parameter (1), disconnected source/sink (0), non-main
parameter (0) and repository system definition (0). Each suite exercises CSV intake,
automatic language selection, main scanning, publication/retrieval, graph inventory,
endpoint coordinates, batch retry suppression and incomplete evidence gates. Fixed input
is explicitly rescanned into a fresh attempt. No model calls occur.

Full automated suite: 629 tests passed, with one existing duplicate-ZIP fixture warning.
Ruff and diff whitespace checks pass. The C suite passed in 37.644 seconds.
Restricted Linux runs use arbitrary UID, read-only root, no network, dropped capabilities
and bounded resources. Each suite performs nine scans including the explicit rescan.

## Limits and next work

Graph signatures do not authenticate libc identity or prove runtime exploitability.
Argument zero, variable/hexadecimal indices, aliases/pointer arithmetic, wide-character
entry points, qualified std::system, macros/build configuration and sanitizer semantics
remain outside acceptance. Withholding all sinks for a local system definition can reduce
recall in repositories that also contain genuine system calls.

Selected suffixes remain .c/.h or .cpp/.h/.hpp. Mixed C/C++, .cc/.cxx, classes/templates,
virtual dispatch and memory-safety coverage are unqualified. Reports remain partial and
qualified triage is unsupported. Zero candidates do not establish a clean result.
Actual bank OCP testing and ground-truth evaluation remain deferred.

Next assess a useful Rust input-source profile within the existing dependency-free Cargo
scope, then review the remaining POC integration gates before deeper per-language modeling.


The initial C acceptance missed the array-style parameter because Joern normalizes
`char *inputs[]` to graph type `char[]*`. A separate native probe showed both that type
and the flow. The selector now recognizes `char**` and `char[]*`; the unchanged array
fixture is rerun in final acceptance. Initial diagnostics remain in
work/slice94-argv-c-linux; probe evidence is in work/slice94-array-probe.


The C++ probe records main:int(int,char**) and an unresolved namespace/signature for the
system call. Its query uses the observed C++ forms and the local-definition exclusion;
it does not claim a resolved libc call. The initial C++ miss and probe remain under
work/slice94-argv-cpp-linux and work/slice94-cpp-probe. C uses its separate unchanged query.


## Recorded Linux results

- c: eight cases passed in 37.644 s; work/slice94-argv-c-linux-final.
  Image `sha256:74320b61a75b13826cd4bb7561841c7279f23bac816ac7faefc45c06f02122e2`.
- cpp: eight cases passed in 36.472 s; work/slice94-argv-cpp-linux-final.
  Image `sha256:b5fa8a0d514807c6ce3ec2e63c8ffc63e840954f9e6bb4e6f44f7a08882b4c7b`.

C acceptance preceded the C++-specific query correction and final limitation wording.
The C query and fixtures are unchanged between these images. Final focused profile and
benchmark compatibility tests: 24 passed.
