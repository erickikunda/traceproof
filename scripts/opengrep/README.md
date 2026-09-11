# C# Opengrep comparison

Opt-in fixture assessment, not a registered production backend. Download the assets in
releases.json to ignored work directories; the runner verifies their release SHA-256
before executing. Signature verification is not performed by this harness.

```sh
uv run python scripts/validate_opengrep_csharp.py \
  --binary work/opengrep/v1.30.0/opengrep --tag v1.30.0 \
  --mode intrafile --output work/opengrep-stable-new
uv run python scripts/validate_opengrep_csharp.py \
  --binary work/opengrep/v2.0.0-nopython-interfile.alpha.2/opengrep \
  --tag v2.0.0-nopython-interfile.alpha.2 --mode interfile \
  --output work/opengrep-alpha-new
```

Output directories must be new. The same local taint rule is applied to Core/MVC/Web API
single-file pairs and global/explicit namespace three-file pairs. Its source is the
fixture Lookup parameter named name; sink is the CommandText assignment RHS. It does
not authenticate framework input or database command types. Expected positives are one
finding and fixed cases zero; exit 1 preserves any failed expectation, even when scans
exit successfully. Every expected source file must appear in scanned paths, with no
reported errors. Native JSON and stderr are retained, along with rule/source hashes.

Copied fixtures have an empty .semgrepignore and --no-git-ignore. This avoids default
exclusion of fixture directories; a zero-file scan must never count as a safe result.
The environment is allowlisted with metrics/version-check suppression requested. OS
network denial is not enforced. Each subprocess has a 120-second timeout; total process
memory and descendant-process containment are not yet qualified. No application code,
package restore, external rule registry or LLM is invoked.

Native dataflow traces are retained for further validation. Finding line/offset agreement
is recorded; this alone does not prove trace completeness or semantic correctness.
The alpha is for testing only and may report a version different from its release tag;
the pinned binary digest is the authoritative identity for this comparison.

Add --combined-only to either command to run the same three classes in one file as a
diagnostic control. Both tested versions miss that positive too. See Slice 76.
