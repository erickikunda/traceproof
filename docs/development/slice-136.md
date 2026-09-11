# Slice 136 — Java deserialization discovery

Added `java-spring-object-read-v1` with separate CWE-502 rule/report identity and
automatic Java selection. Sources remain public Spring GET String RequestParam;
sink is the exact ObjectInputStream.readObject receiver. Native fixtures verify
Base64 decoding, byte-stream constructors and cross-file helper propagation.

Seven restricted Linux native cases passed with counts 1/0/1/0/0/1/0: direct,
constant, cross-file, disconnected, unrelated method, length guard, constructor-only.
Normal intake, source-location validation, publication, exact retrieval and
HTML/JSON/CSV checks passed with zero model calls. 36 focused selection, pipeline
and advisory regressions passed. Ruff and whitespace checks passed.

This qualifies bounded candidate discovery only. Object filters, gadget classes,
runtime reachability and exploitation remain unverified. Existing advisory gates
are unchanged; the new rule has no qualified advisory. No migration or published
container promotion. See [guide](../guides/java-deserialization-discovery.md).

Next: bounded Java XML external-entity feasibility with parser-configuration evidence.
