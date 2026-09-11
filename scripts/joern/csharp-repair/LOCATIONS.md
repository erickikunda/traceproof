# Source-location validation

Replay retained binding-probe outputs without rerunning Joern:

```sh
uv run python scripts/validate_csharp_locations.py \
  --input work/slice78-binding --output work/csharp-location-audit-new.json
```

Output must be new. The input must be trusted local harness output with per-case copied
sources and source hashes. This is an assessment replay tool, not an arbitrary report
upload API. Source paths are resolved and checked under each case's source directory.

The versioned validator runs C# syntax parsing in a bounded child process. Only unique,
exact syntax spans on the raw or following line validate; it preserves the raw node and
records corrected coordinates separately. Ambiguous, malformed, modified, oversized or
unmatched source remains unsupported. A validated span is not proof of node identity,
flow completeness, framework binding or exploitability. Production integration remains
pending. See docs/development/slice-79.md for limits and test evidence.
