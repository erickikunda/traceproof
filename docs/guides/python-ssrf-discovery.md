# Python/Flask SSRF candidates (CWE-918)

Slice 130 adds explicit Joern profile python-flask-ssrf-v1. Bounded Flask request.args/form.get
values flowing to the first positional URL argument of imported requests.get become SSRF
candidates. Top-level requests aliases are recognized; obvious rebinding, foreign imports,
local requests modules and ambiguous same-line endpoints are withheld conservatively.

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern --language python \
  --joern-home /path/to/joern-cli --joern-profile python-flask-ssrf-v1
```

Use normal intake first; scan-import supports the same explicit profile. Default profiles
are unchanged, and selecting this does not also run command/path/SQL checks. The rule ID,
CWE-918 scope, source locations and limitations persist in projection 15 reports and CSV.
There are no automatic model calls. Existing Flask command-injection advisory is not a
valid SSRF evidence policy; this new profile is discovery-only.

Selected sinks are single-line requests.get(URL) or requests.get(URL, timeout=POSITIVE_LITERAL).
Other methods, Session clients, keyword URL, dynamic options, urllib/httpx and framework
variants remain outside this profile. A constant destination is the fixed fixture; tainted
query values passed separately to a constant URL are not part of the modeled sink.

A user-influenced URL does not establish access to a prohibited destination. Redirects,
DNS rebinding, URL interpretation, allowlist effectiveness, credentials and runtime egress
are unresolved. A scheme-only guard does not suppress candidates. No HTTP request is made
by the scanner or fixtures; native validation runs with container network disabled.

The current application wheel was exercised in disposable scratch on the pinned Linux
toolchain. Published scanner image tags are unchanged and do not automatically contain
this profile; rebuild deliberately when packaging the new detection set.
