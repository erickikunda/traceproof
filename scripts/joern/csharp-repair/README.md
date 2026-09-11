# Experimental global-namespace repair (Joern 4.0.625 only)

This one-line patch routes compilation-unit members through the existing astForMembers
helper. That helper marks global type declarations with the parent information consumed
by AstSummaryVisitor. It changes frontend AST construction, not scanned source or graph
call edges after analysis. No downloaded Joern jar is modified.

Retrieve the pinned AstCreator.scala from source_url in manifest.json, then run:

```sh
uv run python scripts/build_joern_csharp_repair.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --source work/slice75-upstream/joern-cli/frontends/csharpsrc2cpg/src/main/scala/io/joern/csharpsrc2cpg/astcreation/AstCreator.scala \
  --output work/csharp-repair-build-new
uv run python scripts/validate_joern_csharp.py \
  --joern-home work/joern-v4.0.625/joern-cli \
  --experimental-classpath work/csharp-repair-build-new/patched-classpath.txt \
  --output work/csharp-repair-validation-new
```

Directories must be new. The builder verifies original and patched source digests,
compiles a class override using installed frontend/compiler jars, and records their
hashes and output class hashes. It does not establish trust in an arbitrary installation;
use the already verified pinned Joern distribution. The override is opt-in, local and
experimental; do not use this classpath mechanism as the production distribution model.

The original runner without --experimental-classpath remains the baseline. Classpath
files execute trusted code and must never come from scanned repositories. Build/runtime
subprocesses are not OS-isolated by this helper. Source coordinates and framework
metadata are unchanged by this patch and remain unqualified.

Before adoption: adversarial namespace/overload/instance-call tests, full upstream test
suite/build, pinned patch packaging, Linux/OCP validation and per-node source mapping.
Prefer an upstream-reviewed fix or qualified release. No upstream issue or PR has been
submitted by this task.
