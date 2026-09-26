# VeriFlow Data Schema & Model Architecture

This document provides a comprehensive technical reference for the data schema, entity relationships, and architectural design choices of the **VeriFlow** platform.

The schema is defined using **SQLAlchemy Declarative Models** with **Alembic migrations** in [`src/veriflow/persistence.py`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py).

---

## Architectural Principles of the Data Tier

1. **Separation of Concerns:** Raw static analysis candidates, human reviewer assertions, and AI advisory verdicts are maintained in separate tables and never conflated or overwritten.
2. **Cryptographic Immutability:** Source code snapshots, evidence bundles, and published reports are content-addressed using SHA-256 hashes (`id = sha256(...)`). Once written, they cannot be modified.
3. **Auditability & Cost Accounting:** Every batch, execution run, LLM token charge, and human review is append-only with strict revision and idempotency keys.

---

## Entity Relationship Diagram (ERD)

```
┌──────────────────┐
│    Repository    │ (Tenancy & Ownership Anchor)
└────────┬─────────┘
         │ 1
         ├────────────────────────────────────────┐
         │ *                                      │ *
┌────────▼─────────┐                     ┌────────▼─────────┐
│     Snapshot     │                     │       Run        │
└────────┬─────────┘                     └────────┬─────────┘
         │ 1                                      │ 1
         ├────────────────────────┐               ├──────────────────────┬──────────────────────┐
         │ *                      │ *             │ *                    │ 1                    │ *
┌────────▼─────────┐     ┌────────▼─────────┐     │             ┌────────▼─────────┐   ┌────────▼─────────┐
│   SourceIndex    │     │   (Linked via    │     │             │   TriageBudget   │   │ PublishedReport  │
└────────┬─────────┘     │    SnapshotID)   │     │             └────────┬─────────┘   └──────────────────┘
         │ 1             └──────────────────┘     │                      │ 1
         │ *                                      │                      │ *
┌────────▼─────────┐                              │             ┌────────▼─────────┐
│   IndexedFile    │                              │             │    TriageCall    │
└──────────────────┘                              │             └────────▲─────────┘
                                                  │                      │ *
                                         ┌────────▼─────────┐            │
                                         │   ScanAttempt    │            │
                                         └────────┬─────────┘            │
                                                  │ 1                    │
                                                  │ *                    │
                                         ┌────────▼─────────┐            │
                                         │    Candidate     │            │
                                         └────────┬─────────┘            │
                                                  │ 1                    │
                                                  │ *                    │
                                         ┌────────▼─────────┐            │
                                         │  EvidenceBundle  │────────────┤
                                         └────────┬─────────┘ 1          │
                                                  │ 1                    │
                                                  │ *                    │
                                         ┌────────▼─────────┐            │
                                         │  OperatorReview  │            │
                                         └──────────────────┘            │
                                                                         │
┌──────────────────┐ 1        * ┌──────────────────┐ 1        * ┌────────┴─────────┐
│   ImportBatch    │───────────►│    ImportItem    │───────────►│       Run        │
└────────┬─────────┘            └──────────────────┘ (Links     └──────────────────┘
         │ 1                     (Row-level state)   via RunID)
         │ *
┌────────▼─────────┐
│  ImportControl   │ (Pause/Resume/Cancel state)
└──────────────────┘
```

---

## Detailed Table Reference

### 1. `repositories`
* **Definition:** [`src/veriflow/persistence.py:L21-L26`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L21-L26)
* **Fields:** `id` (PK, string), `owner` (string), `classification` (string).
* **Reasoning & Need:** Serves as the organizational and multi-tenant security boundary. Before scanning or importing code, the repository must be registered. It defines the authorized sensitivity classification of the source code (`internal`, `restricted`, `synthetic`, etc.), which later dictates whether cloud AI models are permitted to view the code.
* **Relationships:**
  * **1-to-many** with `Snapshot` (`snapshots.repo_id -> repositories.id`).
  * **1-to-many** with `Run` (`runs.repo_id -> repositories.id`).
* **Usage in Codebase:** Used during CSV intake ([`src/veriflow/intake.py:L94-L100`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/intake.py#L94-L100)) to detect conflicting ownership or classification metadata, and during report resolution ([`src/veriflow/reports.py:L35-L43`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/reports.py#L35-L43)) to enforce repository boundaries.

---

### 2. `imports` (`ImportBatch`)
* **Definition:** [`src/veriflow/persistence.py:L28-L35`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L28-L35)
* **Fields:** `id` (PK, UUID), `idempotency_key` (Unique string), `request_sha256` (string), `input_root` (string), `created_at` (timestamp string).
* **Reasoning & Need:** Represents an immutable submission batch (e.g., from `import-csv` or `acquire-git-csv`). Batch intake needs to be idempotent—if an operator resubmits the same CSV with the same key, it must return the existing batch rather than re-creating duplicate runs or throwing unexpected primary key errors.
* **Relationships:**
  * **1-to-many** with `ImportItem` (`import_items.import_id -> imports.id`).
  * **1-to-many** with `ImportControl` (`import_controls.import_id -> imports.id`).
* **Usage in Codebase:** In [`src/veriflow/intake.py:L64-L80`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/intake.py#L64-L80), it stores the hash of the CSV bytes plus the input path, checking for duplicate submissions.

---

### 3. `import_controls`
* **Definition:** [`src/veriflow/persistence.py:L37-L46`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L37-L46)
* **Fields:** `import_id` (PK, FK), `revision` (PK, int), `state` (`active`, `paused`, `cancelled`), `request_key` (string), `reason` (string), `created_at` (timestamp string).
* **Reasoning & Need:** Allows platform operators to pause, resume, or cancel large batch imports midway through processing. By tracking control state as an append-only revision ledger (`(import_id, revision)`), it provides an auditable history of who changed the dispatch state and why.
* **Relationships:**
  * Foreign key to `imports.id`.
  * Unique constraint on `(import_id, request_key)`.
* **Usage in Codebase:** Checked before each item is processed by worker loops in [`src/veriflow/intake.py:L231-L251`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/intake.py#L231-L251) and mutated via CLI commands in [`src/veriflow/import_controls.py:L20-L50`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/import_controls.py#L20-L50).

---

### 4. `import_items`
* **Definition:** [`src/veriflow/persistence.py:L65-L76`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L65-L76)
* **Fields:** `id` (PK, UUID), `import_id` (FK), `row_number` (int), `state` (`ready`, `processing`, `snapshotted`, `rejected`, `failed`), `spec` (JSON), `run_id` (FK to `runs.id`, nullable), `error` (string, nullable), `attempts` (int).
* **Reasoning & Need:** Tracks each individual row in a CSV intake manifest. One malformed archive or bad URL in a 500-repo batch must not fail the entire batch. This table tracks per-item retry attempts (capped at 3) and records granular row-level failure reasons.
* **Relationships:**
  * Child of `imports.id`.
  * Links to `runs.id` once admitted.
  * Unique constraint on `(import_id, row_number)`.
* **Usage in Codebase:** Polled by `worker` processes in [`src/veriflow/intake.py:L224-L290`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/intake.py#L224-L290) to claim ready items, unpack archives, and update execution state.

---

### 5. `snapshots`
* **Definition:** [`src/veriflow/persistence.py:L48-L53`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L48-L53)
* **Fields:** `id` (PK, 64-char SHA-256), `repo_id` (FK), `manifest` (JSON).
* **Reasoning & Need:** The **cryptographic anchor** of VeriFlow. Represents an exact, immutable snapshot of the source code tree. The primary key `id` is the SHA-256 hash of the entire tree manifest (which includes every file path, file size, and file SHA-256). All analysis, candidates, and AI evidence cite this `snapshot_id` to guarantee that code wasn't mutated or modified during scanning.
* **Relationships:**
  * Child of `repositories.id`.
  * Referenced by `runs.snapshot_id` and `source_indexes.snapshot_id`.
* **Usage in Codebase:** Created during intake capture in [`src/veriflow/intake.py:L277-L285`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/intake.py#L277-L285). Verified on disk via [`src/veriflow/indexing.py:L31-L38`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/indexing.py#L31-L38) before any analysis begins.

---

### 6. `runs`
* **Definition:** [`src/veriflow/persistence.py:L55-L63`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L55-L63)
* **Fields:** `id` (PK, UUID), `repo_id` (FK), `state` (`admitted`, `snapshotted`, `failed`), `profile` (`standard`), `snapshot_id` (FK, nullable), `created_at` (timestamp string).
* **Reasoning & Need:** Represents an end-to-end execution instance of scanning a repository. A repository has multiple runs over time as its code changes. The `Run` binds an admitted intake item to an immutable `Snapshot`.
* **Relationships:**
  * Child of `repositories.id`.
  * Optional foreign key to `snapshots.id`.
  * Parent to `ScanAttempt`, `CodeqlAttempt`, `TriageBudget`, `TriageCall`, and `PublishedReport`.
* **Usage in Codebase:** The primary lifecycle coordinator referenced across CLI commands like `run-status`, `scan-run`, and report queries in [`src/veriflow/reports.py:L35-L42`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/reports.py#L35-L42).

---

### 7. `source_indexes` & `indexed_files`
* **Definitions:** [`src/veriflow/persistence.py:L78-L95`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L78-L95)
* **`SourceIndex` Fields:** `id` (PK, UUID), `snapshot_id` (FK), `version` (parser version string), `state` (`building`, `published`), `report` (JSON summary, nullable).
* **`IndexedFile` Fields:** `id` (PK, UUID), `index_id` (FK), `path` (string), `result` (JSON syntax/AST inventory).
* **Reasoning & Need:**
  * VeriFlow performs syntactic indexing (function definitions, AST symbol tables, direct calls) before running expensive security scans.
  * `SourceIndex` records whether the snapshot successfully parsed (syntax readiness gate).
  * `IndexedFile` persists per-file checkpoints. If an indexing worker dies midway through a large repository, it can resume from the last indexed file without re-parsing from scratch.
* **Relationships:**
  * `source_indexes` links to `snapshots.id` (Unique on `(snapshot_id, version)`).
  * `indexed_files` links to `source_indexes.id` (Unique on `(index_id, path)`).
* **Usage in Codebase:** Written by [`src/veriflow/indexing.py:L56-L95`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/indexing.py#L56-L95) and inspected by `static_readiness()` in [`src/veriflow/readiness.py:L15-L55`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/readiness.py#L15-L55) to ensure code parsed cleanly before LLM triage or report publication.

---

### 8. `scan_attempts` (and legacy/reference `codeql_attempts`)
* **Definition:** [`src/veriflow/persistence.py:L97-L110`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L97-L110)
* **Fields:** `id` (PK, UUID), `run_id` (FK), `created_at` (timestamp string), `report` (JSON metadata, scanner version, exit diagnostics, query SHA-256).
* **Reasoning & Need:** A single `Run` can have multiple static scan attempts (e.g., retried queries, adjusted timeouts, or comparing CodeQL and Joern). This table stores the durable diagnostic record of the analyzer execution, including exit codes, warnings, and SARIF file pointers—even when the scan fails or times out.
* **Relationships:**
  * Child of `runs.id`.
  * Parent to `Candidate` (`candidates.attempt_id -> scan_attempts.id`).
* **Usage in Codebase:** Populated by [`src/veriflow/joern.py:L74-L96`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/joern.py#L74-L96) and [`src/veriflow/scanning.py:L40-L75`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/scanning.py#L40-L75); joined during report publication in [`src/veriflow/reports.py:L52-L66`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/reports.py#L52-L66).

---

### 9. `candidates`
* **Definition:** [`src/veriflow/persistence.py:L112-L119`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L112-L119)
* **Fields:** `id` (PK, UUID), `attempt_id` (FK), `fingerprint` (64-char SHA-256), `evidence` (JSON).
* **Reasoning & Need:** Stores raw, unreviewed alerts emitted by static analysis tools (SARIF results).
  * **Critical Concept:** Alerts are *candidates*, not verified vulnerabilities.
  * **Deduplication:** The `fingerprint` column hashes `[snapshot_id, tool_driver, rule_id, path, sink]`. This prevents cosmetic code formatting or line-number shifts from creating duplicate alerts across scans.
* **Relationships:**
  * Child of `scan_attempts.id`.
  * Unique constraint on `(attempt_id, fingerprint)`.
  * Parent to `EvidenceBundle`.
* **Usage in Codebase:** Extracted from SARIF files via `fingerprint()` in [`src/veriflow/sarif.py:L60-L66`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/sarif.py#L60-L66).

---

### 10. `evidence_bundles`
* **Definition:** [`src/veriflow/persistence.py:L121-L126`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L121-L126)
* **Fields:** `id` (PK, SHA-256 of canonical JSON content), `candidate_id` (FK), `content` (JSON payload).
* **Reasoning & Need:** Generative AI models should never receive entire codebases. This table stores the strictly bounded context extracted for a single candidate: entry point, intermediate flow hops, and the sink function (strictly $\le$8 locations, $\le$16 KiB of source code, and $\le$32 KiB total payload). The table is content-addressed—`id` is the exact SHA-256 digest of the bundle content.
* **Relationships:**
  * Child of `candidates.id`.
  * Referenced by `triage_calls.bundle_id` and `operator_reviews.bundle_id`.
* **Usage in Codebase:** Constructed by [`src/veriflow/bundles.py:L38-L105`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/bundles.py#L38-L105) and retrieved before invoking LLMs in [`src/veriflow/triage.py:L109-L115`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/triage.py#L109-L115).

---

### 11. `triage_budgets` & `triage_calls`
* **Definitions:** [`src/veriflow/persistence.py:L128-L147`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L128-L147)
* **`TriageBudget` Fields:** `run_id` (PK, FK), `limit_micro_usd` (BigInteger), `max_requests` (int, default 100).
* **`TriageCall` Fields:** `id` (PK, UUID), `run_id` (FK), `bundle_id` (FK), `request_key` (unique per run), `request_sha256`, `created_at`, `state`, `charged_micro_usd` (BigInteger), `result` (JSON).
* **Reasoning & Need:**
  * **Cost Control Ledger:** Prevents runaway cloud LLM expenditures. `TriageBudget` establishes an immutable financial ceiling before scanning begins (1,000,000 micro-USD = $1.00).
  * **Idempotency & Accounting:** `TriageCall` records every single AI invocation, token count, micro-dollar charge, model name, and verdict. If an operator retries a triage call with the same `request_key`, VeriFlow returns the existing cached result without charging or calling the provider again.
* **Relationships:**
  * `triage_budgets` is 1-to-1 with `runs.id`.
  * `triage_calls` links to `runs.id` and `evidence_bundles.id` (Unique on `(run_id, request_key)`).
* **Usage in Codebase:** Managed in [`src/veriflow/triage.py:L19-L55`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/triage.py#L19-L55) and [`L150-L185`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/triage.py#L150-L185). Enforces budget reservations prior to provider invocation.

---

### 12. `operator_reviews`
* **Definition:** [`src/veriflow/persistence.py:L163-L176`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L163-L176)
* **Fields:** `id` (PK, SHA-256), `candidate_id` (FK), `bundle_id` (FK), `revision` (int), `request_key` (string), `request_sha256` (string), `content` (JSON containing `reviewer_label`, `state`, `rationale`, `evidence_ids`).
* **Reasoning & Need:** Allows human security analysts to record formal review decisions (`confirmed`, `false_positive`, `needs_review`, `deferred`). Crucially, human assertions are kept in an **append-only revision ledger** (`revision = 0, 1, 2...`). They never overwrite or mutate the raw candidate or the model's triage advice.
* **Relationships:**
  * Child of `candidates.id` and `evidence_bundles.id`.
  * Unique on `(candidate_id, revision)` and `(candidate_id, request_key)`.
* **Usage in Codebase:** Recorded via [`src/veriflow/reviews.py:L70-L125`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/reviews.py#L70-L125). Embedded alongside machine findings in reports via [`src/veriflow/reports.py:L175-L181`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/reports.py#L175-L181).

---

### 13. `published_reports`
* **Definition:** [`src/veriflow/persistence.py:L149-L161`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L149-L161)
* **Fields:** `id` (PK, 64-char SHA-256), `run_id` (FK), `version` (int), `input_digest` (SHA-256), `created_at` (timestamp string), `content` (JSON document).
* **Reasoning & Need:** The final deliverable. Contains the materialized summary joining scan results, coverage metrics, candidate rows, triage calls, and operator reviews.
  * **Immutability & Integrity:** The `id` is the exact SHA-256 digest of the canonical report JSON.
  * **Versioned Evolution:** If a new operator review is added tomorrow, publishing again creates `version = 2` with a new `id`, preserving `version = 1` for audit compliance.
* **Relationships:**
  * Child of `runs.id`.
  * Unique on `(run_id, version)` and `(run_id, input_digest)`.
* **Usage in Codebase:** Generated in [`src/veriflow/reports.py:L252-L287`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/reports.py#L252-L287) and projected to HTML, Markdown, CSV, and SARIF exports.

---

### 14. `benchmark_scorecards`
* **Definition:** [`src/veriflow/persistence.py:L178-L184`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/persistence.py#L178-L184)
* **Fields:** `id` (PK, 64-char SHA-256), `dataset_id` (string), `created_at` (timestamp string), `content` (JSON metrics).
* **Reasoning & Need:** Used by the evaluation suite to measure detection recall against ground-truth datasets (such as the 50-repository known vulnerability benchmark). It decouples testing metrics from active production scans, persisting versioned precision/recall scorecards without re-running scans.
* **Relationships:**
  * Standalone entity indexed by `dataset_id`.
* **Usage in Codebase:** Saved via `benchmark-publish` in [`src/veriflow/benchmark.py:L35-L65`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/benchmark.py#L35-L65) and retrieved/compared via [`src/veriflow/benchmark_comparison.py`](file:///Users/eric/PycharmProjects/traceproof/src/veriflow/benchmark_comparison.py).

---

## Summary Reference Table

| Table Name | Entity Represented | Primary Key Pattern | Key Foreign Keys | Purpose / Codebase Role |
| :--- | :--- | :--- | :--- | :--- |
| **`repositories`** | Application Tenancy | Natural String ID | None | Tenancy root, ownership, and regulatory data classification. |
| **`imports`** | Ingestion Batch | UUID | None | Idempotent tracking of CSV manifest batch submissions. |
| **`import_controls`** | Batch Controls | `(import_id, revision)` | `import_id` | Audit trail for pause, resume, and cancel dispatch commands. |
| **`import_items`** | Manifest Row | UUID | `import_id`, `run_id` | Granular per-archive unpack status, errors, and retry counter. |
| **`snapshots`** | Source Tree | SHA-256 Digest | `repo_id` | Cryptographic anchor storing immutable file inventory & hashes. |
| **`runs`** | Scan Execution Lifecycle | UUID | `repo_id`, `snapshot_id` | Central workflow entity connecting source snapshots to scans. |
| **`source_indexes`** | Syntax & Parsing Gate | UUID | `snapshot_id` | AST parsing readiness status; flags incomplete language coverage. |
| **`indexed_files`** | File Parsing Cache | UUID | `index_id` | Per-file checkpoint table allowing indexing to resume on interrupt. |
| **`scan_attempts`** | Analyzer Execution | UUID | `run_id` | Durable record of Joern / CodeQL execution and exit diagnostics. |
| **`candidates`** | Unreviewed SAST Alert | UUID (Unique Fingerprint) | `attempt_id` | Structural finding alerts with deduplicated flow signatures. |
| **`evidence_bundles`** | Targeted Code Context | SHA-256 Digest | `candidate_id` | Self-contained, bounded ($\le$16 KiB) source slice for LLM review. |
| **`triage_budgets`** | Financial Cost Cap | `run_id` | `run_id` | Pre-allocated micro-USD budget and max request limit per run. |
| **`triage_calls`** | AI Invocation Ledger | UUID (Unique Req Key) | `run_id`, `bundle_id` | Immutable ledger of token usage, micro-dollar cost, and verdicts. |
| **`operator_reviews`** | Human Review Decision | SHA-256 Digest | `candidate_id`, `bundle_id` | Append-only revision ledger of human analyst confirmations/dismissals. |
| **`published_reports`**| Published Output | SHA-256 Digest | `run_id` | Immutable versioned deliverable projected into HTML, JSON, and CSV. |
| **`benchmark_scorecards`** | Recall Evaluation | SHA-256 Digest | None | Offline quality metrics scored against ground-truth benchmarks. |
