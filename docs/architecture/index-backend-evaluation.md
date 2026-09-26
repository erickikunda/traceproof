# Syntax inventory versus Joern CPG indexing

## Decision being evaluated

VeriFlow currently separates lightweight syntax evidence from semantic vulnerability
discovery. The persisted `index-run` contract is presently a Python inventory of files,
functions and unresolved calls. Language-specific Tree-sitter parsers also serve as bounded,
independent evidence gates for scanner paths. Joern builds the richer Code Property Graph used
by vulnerability discovery.

This experiment does not assume either implementation wins. It asks whether Joern can replace
the persisted syntax inventory for the same input and contract at acceptable cost and quality.
It does not remove the language-specific evidence gates or change vulnerability profiles.

## Options and tradeoffs

| Option | Advantages | Costs and risks |
|---|---|---|
| Keep syntax inventory and Tree-sitter evidence gates | Fast per-file work; exact byte/source spans; per-file failure isolation and checkpoints; independent verification of scanner claims; small memory and scratch footprint | Maintains parser-specific code; syntax calls remain unresolved; semantic relationships require the scanner stage |
| Replace inventory with Joern | One graph can support inventory plus semantic queries; richer calls/types/control/data flow where the frontend resolves them; potential CPG reuse across profiles | JVM/frontend startup and larger CPU, RAM and scratch requirements; language-level failure unit; normalized nodes differ from written syntax; frontend quality varies; source coordinates and signatures can be unresolved; loss of an independent verifier if evidence gates are also removed |
| Hybrid, recommended | Syntax inventory remains dependable; one cached Joern CPG supplies semantic analysis; outputs can corroborate each other | Two representations exist and must be versioned; extraction reuse and artifact lifecycle need deliberate implementation |
| Selectable comparison, implemented POC | Produces evidence from the same immutable snapshot; preserves default behavior; lets language-specific results guide a later decision | Initial comparison is Python-only and bounded to 1,000 records; peak RSS and throughput need container/platform telemetry |

## Why a CPG is not a drop-in syntax tree

Tree-sitter parses written source into a concrete, location-oriented syntax tree. Joern
frontends translate source into a normalized Code Property Graph containing AST-derived nodes,
calls, control flow and data-flow structures. Normalization is useful for security queries but
can introduce temporary nodes, alter names, omit syntax detail or retain unresolved signatures.

The service-level objectives also differ. Inventory should cheaply enumerate captured content
and report partial parsing file by file. CPG construction is a heavier language-level stage. A
timeout or frontend failure must therefore be reported as unknown coverage, never as an empty or
clean result.

Independent evidence is a material control. A Joern path can be checked against the immutable
snapshot by a different parser. Making one frontend both the producer and sole verifier of a
claim creates correlated failure and can turn a frontend mapping defect into a published finding.

## Fair evaluation protocol

Freeze the source snapshot, Joern/frontend version, syntax parser versions, resource limits and
dependency configuration. Run both backends from the same admitted `run_id`. Do not merge their
outputs. Compare:

- represented and omitted files;
- symbol and call counts plus normalized exact overlap;
- source path and line agreement;
- unsupported, malformed, timed-out and truncated inputs;
- cold and warm elapsed time;
- peak resident memory from container/OpenShift telemetry;
- scratch/CPG artifact bytes;
- deterministic repeatability and failure recovery;
- downstream candidate preservation, assessed separately from inventory quality.

Use the 50 labeled repositories only after the inventory contract is stable. Add large,
mixed-language and intentionally malformed repositories. Predefine acceptance thresholds before
examining results. A richer count is not automatically better, and a smaller count is not
automatically more precise.

## Implemented POC boundary

`index-run --backend syntax` is the unchanged default. `--backend joern` produces a separate
versioned Python inventory from a pinned Joern CPG. `compare-indexes` creates/reuses both indexes
for one snapshot and returns their reports plus normalized overlap/delta metrics.

The Joern index is Python-only because that is the current persisted inventory contract. It does
not claim parity with the separate language-specific evidence parsers. It has no per-file CPG
checkpoint, uses a requested 2-GiB JVM heap, records extraction/query elapsed time and artifact
bytes, and declares that peak RSS requires container telemetry. Neither backend performs a
security scan or returns a vulnerability verdict.

## Decision rule

Adopt Joern as the default inventory only for a language where measured coverage, location
quality, failure behavior and operating cost satisfy predefined thresholds. Even then, retain a
minimal independent source-span verifier for finding publication. A decision for one frontend
must not automatically apply to every supported language.
