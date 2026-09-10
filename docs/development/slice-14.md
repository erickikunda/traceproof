# Slice 14: explicit report selection and freshness

`traceproof resolve-report REPO_ID --selection latest-attempt` returns a JSON selection envelope containing the current admitted run/attempt state and its published report, if available. It never silently falls back.

`traceproof resolve-report REPO_ID --selection latest-completed` selects the most recent published report whose recorded `static_review_readiness.state` is `ready_for_review`. Completion means the existing Python parsing/static execution gate only; it does not mean security completeness or a clean repository. Legacy reports lacking that gate are ineligible.

The envelope includes `selected_report_id`, `selected_is_latest_attempt`, latest run/attempt IDs and status, warnings, and the immutable report itself. A missing eligible publication produces a null report and an explicit warning. A newer failed, incomplete or unpublished attempt remains visible even when an older review-ready report is selected. Consumers should retain this envelope with dashboard exports rather than presenting the embedded historical report as current. Use the selected ID with `get-report --report-id` to retrieve existing HTML/Markdown/CSV representations.

Selection orders run admission, then attempt creation, then report version, with deterministic ID tie-breakers. Republishing old work does not make it newer source work. Publication and current-state disclosure remain separate: exact report retrieval and hashes are unchanged. These reads execute neither scans nor model calls and create no artifacts. Selection is bounded to 10,000 report versions per repository and fails explicitly above that limit; indexed fleet selection is future work.

No migration is required. Tests cover review-ready selection, newer failed work before and after publication, immutable exact retrieval, missing publications, invalid mode and repository isolation. Existing format/integrity tests remain applicable. This closes the initial selection gap in M2.8; full coverage/finding semantics and fleet performance remain open.
