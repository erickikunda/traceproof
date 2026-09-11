"""Validate saved local GCS handoff results; does not run scans or access cloud services."""

import argparse
import json
from pathlib import Path

LANGUAGES = ("java", "python", "javascript", "typescript", "go", "c", "cpp", "csharp", "rust")


def summarize(paths):
    rows = []
    keys = set()
    for path in paths:
        data = json.loads(Path(path).read_text())
        key = (data["language"], data["fixture_case"])
        if key in keys:
            raise ValueError("Duplicate language/case result")
        keys.add(key)
        if (
            key[0] not in LANGUAGES
            or key[1] not in ("vulnerable", "fixed")
            or data["passed"] is not True
            or data["candidate_count"] != (1 if key[1] == "vulnerable" else 0)
            or data["cloud_calls"] != 0
            or data["model_calls"] != 0
            or data["ocp_qualified"] is not False
        ):
            raise ValueError("Result does not meet local fixture acceptance")
        rows.append(data | {"validation_path": str(path)})
    required = {(lang, case) for lang in LANGUAGES for case in ("vulnerable", "fixed")}
    if keys != required:
        raise ValueError("Require all nine language vulnerable/fixed pairs")
    if len({row["acquisition_image"] for row in rows}) != 1:
        raise ValueError("Mixed acquisition images require separate acceptance")
    for lang in LANGUAGES:
        if len({row["scanner_image"] for row in rows if row["language"] == lang}) != 1:
            raise ValueError("Pair uses different scanner images")
    return dict(
        schema_version="1",
        passed=True,
        cases=sorted(rows, key=lambda row: (row["language"], row["fixture_case"])),
        cloud_calls=0,
        model_calls=0,
        ocp_qualified=False,
        quality_benchmark=False,
        scope="Synthetic SDK handoff and bounded scanner fixtures; no live GCS qualification",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.results), indent=2))


if __name__ == "__main__":
    main()
