# Local acceptance command

Review retained evidence without Docker, cloud access or model calls:

```sh
uv run python scripts/local_acceptance.py work/new-acceptance
```

The output folder must not exist. acceptance.json distinguishes passed, failed, not_run
and deferred checks. matrix.json records the 18 validated language/case results. Default
mode reads the paths in containers/gcs-acceptance-matrix.json and verifies report/receipt
artifacts, not just pass flags. work/ artifacts are intentionally untracked; a fresh clone
may lack them. Missing artifacts fail the check rather than silently accepting the inventory.
Retained evidence does not prove the current checkout or current image tags passed again.

For an explicit fresh run of all 18 GCS fixture handoffs:

```sh
uv run python scripts/local_acceptance.py work/new-native-acceptance --run-native
```

Prepare the image tags documented in the GCS guide first. Runs are sequential and bounded;
expect several minutes and adequate Docker/storage capacity. This command uses the synthetic
SDK boundary, real scanner containers and no cloud/model calls. It does not build or pull
images, migrate databases, push artifacts, apply OCP manifests or configure credentials.
A Docker/subprocess timeout is reported as failed; inspect Docker for leftover containers
before retrying after forced termination. No automatic cleanup of unrelated jobs occurs.

Add --tests to run the local pytest suite with its log retained. Without it, application
checks explicitly say not_run. Git transport/private HTTPS and plain archive native tests
have separate validators and are also explicitly not_run here. This command is a local
GCS language acceptance entrypoint, not a replacement for every validation script.

Exit 1 means a local check failed. Exit 0 means the selected local checks passed with
external gates still deferred; it never means production ready. The six external gates
cover real cloud, bank Git, bank models, required OCP dev acceptance, ground truth and fleet
qualification. No bank credentials or code are needed for these local checks.
