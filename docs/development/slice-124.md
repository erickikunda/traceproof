# Slice 124 — Specialized projection 14 images

Rebuilds C# and Rust smoke images from their existing pinned toolchain bases and the current
application wheel. New GCS-specific tags preserve prior qualified images. Installed wheel
and dependency-lock hashes are checked against build inputs. The Google SDK stays in the
separate acquisition image; offline scanner dependencies are unchanged.

The GCS handoff validator now accepts --language c/csharp/rust and --case vulnerable/fixed,
using existing fixtures rather than inventing broader query coverage. Each test exports
synthetic SDK-boundary archive bytes, captures a receipt-bound snapshot and runs the real
bounded scanner in a separate restricted, network-disabled container.

Acceptance: C# and Rust vulnerable/fixed pairs each produce 1/0 candidates. All four runs
export projection 14 reports with snapshot_bound GCS generation 123 and incomplete coverage.
Runtime probes pass; zero cloud/model calls. No bank OCP or live GCS acceptance. Exact image
IDs and validation paths are in containers/gcs-specialized-images.json.

No application/schema/toolchain change, migration, image push or commit. Build/pip/input-hash
checks and Ruff pass; prior full application suite remains the baseline. Next exercise
remaining general-language selections with the current image and consolidate the local
acceptance matrix. No extra C# or Rust semantic refinement is introduced.
