# Slice 119 — GCS archive acquisition contract

Introduces an internal ArchiveReader protocol and acquire_archive service. An explicit
bucket allowlist, object name, positive generation, expected SHA-256 and bounded size/time
settings precede acquisition. Reader metadata must match the exact requested version.
The streamed result must match both declared size and expected digest before archives.csv
is published. Source filenames are generated locally, never derived as paths from object keys.
Failed operations remove partial archive/CSV and retain a sanitized failure receipt.

Five local adapter tests pass: valid ZIP handoff, no overwrite, bucket rejection before I/O,
version mismatch, truncated size and digest mismatch. No Google SDK, network client, CLI,
credentials or real GCS call is introduced. No migration, model call or image change.

This contract does not yet authenticate cloud metadata. Its receipt stays with the handoff;
GCS metadata is not imported as Git provenance or represented as a Git commit. Offline
intake must still validate/unpack the archive. The deadline is checked between chunks;
the future network reader must enforce its own blocking-I/O deadlines and generation
preconditions. Process/storage limits remain needed for hard resource enforcement.

Next implement the live generation-pinned GCS reader and operator CLI, with mocked HTTP
or SDK boundary tests, followed by durable GCS provenance. Real bank GCS acceptance remains
pending authorized connectivity and operator-managed credentials.
