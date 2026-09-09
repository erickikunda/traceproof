# Slice 10 — Evaluator-only benchmark contracts

Slice 09 is committed as `a62e47c`. This slice implements M0.7's initial local benchmark
manifest and label interface. It prepares for the existing 50-repository corpus without
requiring its source or labels on the personal laptop. No benchmark evaluation is run.

## Separate inputs

`benchmark-schema` emits two strict JSON schemas. Both reject unknown fields, duplicate
JSON keys and incorrect types. Documents are limited to 1 MiB each.

| Document | Fields and purpose |
| --- | --- |
| Manifest | Schema/dataset versions and 1–1,000 unique repository entries: repository ID, TraceProof snapshot ID, languages, declared CWE scope and label completeness |
| Labels | Dataset/label-set versions, canonical manifest SHA-256 and at most 20,000 labels with label ID, repository/snapshot, root-cause ID, CWE, normalized source path, file SHA-256, line range, symbol and adjudication reference |

Manifest repositories permit `known_positives_only` or `exhaustive_for_declared_scope`.
Completeness is an assertion by the dataset owner, not something this validator proves.
Duplicate repository IDs, label IDs and root-cause units are rejected. A vulnerability
unit is one `(repo_id, snapshot_id, root_cause_id)`; multiple observations of that root
cause cannot become multiple labels under this contract. Distinct root causes at one
location may have distinct labels. More sophisticated matching remains evaluator work.

Labels must belong to the pinned manifest's dataset, repository, snapshot and CWE scope.
Paths reject absolute/traversal/backslash/non-normalized forms. Lines must be positive
integers with an ordered range; symbol and adjudication reference must be nonblank.
The checker does not prove that a declared symbol or line actually describes a defect.

## Commands and digest workflow

```bash
uv run traceproof benchmark-check examples/benchmark-manifest.json
uv run traceproof benchmark-check examples/benchmark-manifest.json --labels examples/benchmark-labels.json
uv run traceproof --state-dir /absolute/state benchmark-check /absolute/manifest.json \
  --labels /absolute/labels.json --check-local-snapshots
```

The manifest-only result returns `manifest_sha256`, computed from the validated canonical
JSON representation (sorted keys and compact encoding). Use it in the separate label
document. Whitespace/key ordering changes do not alter this pin; changing manifest content
requires a new pin. A label-set digest is also returned when labels are supplied.

Without local alignment, checking needs no initialized database. Optional alignment reads
stored snapshot metadata and verifies snapshot ownership, label file membership and file
digest equality. Missing snapshots or mismatched files produce `alignment_incomplete`,
structured issue codes and CLI exit code 1. Invalid contracts/pins also exit nonzero with
errors that omit submitted field values. It does not reread source bytes, verify line
semantics, resolve Git revisions, acquire archives or create scan/model tasks.

The committed examples contain placeholder snapshot/file digests. They demonstrate the
contract and correctly fail local alignment unless replaced with real pinned metadata.
A separate local synthetic test aligned labels to the Slice 09 acceptance snapshot.

## Isolation and honest metrics

The checker lives in an evaluator-specific module and reads explicitly supplied paths.
Scan workers, bundle construction and model requests receive no label objects from it.
Manifest and label files must remain outside analyzed source archives. This is an API
and workflow separation, not OS-enforced multi-user isolation; enterprise evaluator
identities/storage permissions remain future work. No label database tables are added.

Results contain contract identifiers/digests, counts and alignment codes, omitting raw
root-cause descriptions, source locations and adjudication references. `evaluation_performed`
is false; precision and recall remain null. Zero labels or unlisted findings do not imply
absence of vulnerabilities. In particular, additional predictions must remain unjudged
until adjudicated rather than being counted automatically as false positives.

## Validation and remaining work

225 tests passed. New cases cover manifest pins, foreign snapshots/CWEs, duplicate units,
unsafe paths, strict numeric ranges, empty provenance, unknown fields, duplicate JSON
keys, document size, successful/mismatched local alignment, CLI exit codes and no new
scan/model records. The inherited duplicate ZIP fixture emits one expected warning.

Remaining M4 work includes durable dataset registration, authorized source acquisition,
revision/label applicability review, frozen scan configuration, evaluator-only dispatch,
one-to-one prediction matching, ambiguous/unjudged queues, metrics and benchmark reports.
The 50-repository dataset has not been loaded or evaluated. Schema remains 0005; no
migration or paid provider call is required by this slice.
