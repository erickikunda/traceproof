# Slice 29: self-contained HTML benchmark scorecards

```bash
uv run veriflow benchmark-get DATASET_ID SCORECARD_ID --format html > scorecard.html
```

The HTML view renders an exact saved scorecard without reading label inputs, rerunning
evaluation, scanning or calling models. `benchmark-evaluate ... --format html` also works,
but that command evaluates its supplied inputs as usual and does not persist the result.

The page presents candidate-recall proxy numerator/denominator and percentage, evaluation
completion, repository outcomes, per-CWE metrics and scope gaps. Expandable sections retain
label/candidate details and provenance/configuration hashes. Limitations remain visible.
Precision and confirmed recall remain explicitly unknown. Missing metrics show Unknown;
legacy scorecards do not acquire invented per-CWE results. Additional predictions remain
unjudged. A complete evaluation is not proof of complete security coverage.

This is an escaped, script-free HTML document with inline CSS, no remote assets or outbound
links and a restrictive content security policy. Wide tables scroll. Expand detail sections
before printing. JSON/CSV remain the authoritative machine-readable projections. HTML is a
presentation of the stored scorecard, not a signed artifact; editing the exported file does
not modify or republish the original. Repository and label identities may be sensitive, so
share according to the dataset's audience permissions. No raw source is added by the view.

Tests cover exact saved retrieval after input removal, metric preservation, incomplete and
unknown states, legacy handling and hostile text escaping without executable markup.
No schema migration or evaluator-version change is required. This completes another local
M4.7 output format, but benchmark qualification and adjudicated quality measures remain open.
