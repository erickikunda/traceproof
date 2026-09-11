# Slice 140 — C# file-path discovery

Added `csharp-query-file-read-v1` with CWE-22 report identity, mapped query-source
gating and automatic selection. The native probe found an unresolved .NET signature;
selection is explicitly limited to fully qualified receiver syntax and one argument.
Source-defined System/IO/File type lookalikes conservatively exclude the profile.
No general API binding or directory-escape claim is made.

Eight restricted repaired-C# Linux native fixtures passed: direct, constant,
cross-file, disconnected, unrelated method, local File type, unbound input and
path guard. Counts 1/0/1/0/0/0/0/1. Source mapping, publication, exact retrieval and
HTML/JSON/CSV checks passed with zero model calls. 42 focused mapping, selection,
pipeline and advisory tests passed; Ruff and whitespace checks passed.

No migration, new advisory qualification or published-image promotion. See
[guide](../guides/csharp-file-discovery.md). Next bounded C# process-execution
feasibility with explicit argument/option evidence.
