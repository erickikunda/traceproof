# Python/Flask file-path discovery (CWE-22)

Slice 128 adds opt-in Joern profile python-flask-path-v1. It reports a path-traversal
candidate when bounded Flask request.args/form.get input reaches the first positional
argument of an unshadowed builtin open call. Only single-line calls and omitted or constant
r/rb/rt modes are selected. Direct assignment/concatenation and a cross-file helper have
fixtures. Existing system/eval profiles and default language selection are unchanged.

After normal archive intake creates RUN_ID:

```sh
traceproof --state-dir /path/to/state scan-run RUN_ID --engine joern --language python \
  --joern-home /path/to/joern-cli --joern-profile python-flask-path-v1
```

Use scan-import with the same options for an admitted batch. Persisted reports retain the
profile, CWE-22 scope and candidate source locations. Projection 15 exports cwe_scope and
discovery_profile in scan/candidate CSV as well as JSON; HTML contains the report details.
An empty cwe_scope on older/unmodeled profiles means unspecified, not zero possible CWEs.

This profile is discovery-only. Do not attach the Flask command-injection advisory policy:
its source/sink claims do not qualify file access. No automatic model call or false-positive
dismissal is added. A user-controlled path is not proof of escaping an intended directory;
confinement, permissions, runtime builtin identity and exploitability remain unverified.
A nearby '..' check does not suppress the candidate. Write modes, keyword arguments,
pathlib, framework file-serving APIs, dynamic monkeypatching and general sanitizer reasoning
are not supported by this bounded profile. Shadowed open bindings are withheld conservatively.

Native acceptance uses a pinned existing Linux toolchain image with the new wheel installed
into disposable scratch. Published image tags are not rebuilt or promoted by this slice;
use the current installed application or explicitly rebuild an appropriate image. Existing
GCS matrix images continue to describe their historical projection 14 behavior.
