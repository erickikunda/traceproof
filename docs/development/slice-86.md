# Slice 86 — Go durable Joern integration

Added joern-go-discover with a separate packaged lookup(input)/Command argument-3
profile. It uses the existing durable scan lifecycle, SARIF candidates, report retrieval,
HTML/JSON publication and evidence-bundle gates. Only .go sources and go.mod metadata
are prepared. Graph inventory counts source files separately; both source and metadata
are hash-checked before and after scanning. Other files remain omitted.

The subprocess environment disables Go proxy/checksum downloads and automatic toolchain
fetching (GOPROXY=off, GOSUMDB=off, GOTOOLCHAIN=local). These settings are not OS network
isolation. No application build or repository script execution is requested.
Call-name selection does not authenticate os/exec.Command or prove shell execution.
Frameworks, dependencies, cgo, build tags and advanced semantics remain unqualified.
All reports remain partial/non-adjudicated, including zero candidates; qualified triage
and automatic result reuse remain unsupported.

Real restricted Linux ARM64 acceptance passed five existing dependency-free module
fixtures in 25.103 seconds: single-file vulnerable/fixed 1/0, three-package cross-file
vulnerable/fixed 1/0, disconnected input 0. All returned snippets matched their reported
source lines and all selected source files appeared in graph inventory. Persisted reports
remained incomplete and evidence bundles retained unsupported qualified-triage status.
This is bounded fixture evidence, not portfolio recall or production throughput.

Image: sha256:d9a6e4d26ff0f1b08560eaf825aa519c6fd8aa7f975424fcbe9d2e85acd6c790.
Offline image layer atop the trusted local Joern base. Runtime uses arbitrary UID,
read-only root, no network, dropped capabilities, no-new-privileges and bounded
CPU/memory/PID/tmpfs resources. Artifacts: work/slice86-go-linux. No LLM calls.

548 regression tests passed (one existing duplicate-ZIP warning). The additional
module-selection assertion then passed all 30 shared Joern tests. Lint, formatting,
package build and whitespace checks passed. No migration or user action required.
Changes remain uncommitted. Next Rust durable integration and minimum Linux acceptance;
C/C++ follows the current language plan. Broader detection/benchmarking and bank OCP
validation remain separate gates.
