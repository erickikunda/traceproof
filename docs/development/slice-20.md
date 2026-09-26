# Slice 20: saved benchmark regression comparison

```bash
uv run veriflow benchmark-compare DATASET_ID BASELINE_SCORECARD_ID CURRENT_SCORECARD_ID
uv run veriflow benchmark-compare DATASET_ID BASELINE_SCORECARD_ID CURRENT_SCORECARD_ID --format markdown
```

Comparison retrieves exact immutable scorecards with dataset and integrity checks. It
does not read evaluator inputs, run scans, call models, or save another publication.
Migration 0007 remains current.

Comparable inputs require equal scorecard schema, evaluator version, manifest and label
digests, profile, selected rule set and label population; both evaluations must be complete
and have labels. Incompatible inputs disclose reasons and original metrics, but produce
null deltas and no per-label transitions. An incomplete run never appears as improvement.

Query digests and CodeQL versions may differ so rule/tool upgrades can be compared against
the same frozen corpus. All analysis-scope differences are disclosed. This does not prove
which configuration change caused a result; query pins still omit transitive dependencies.

Comparable results show matched-label and recall-proxy deltas (current minus baseline),
plus per-label unchanged/location-match-gained/location-match-lost transitions. A proxy
delta is a fraction, not a percentage-point integer. Gains/losses describe provisional
location matching, not confirmed discoveries or fixes. Precision and confirmed recall
deltas stay null. Cost/latency comparison is not supported by current scorecard contents.

JSON and escaped Markdown outputs are available. Tests cover gain/loss direction,
identical IDs, incompatible populations/versions, empty labels, selected-rule changes,
dataset ownership and CLI rendering. M4.8 is partially addressed; model attribution,
cost regression and adjudicated release gates remain open.
