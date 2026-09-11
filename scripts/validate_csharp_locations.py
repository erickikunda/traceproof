"""Replay retained Slice 78 paths through conservative C# source-span validation."""

import argparse
import json
from pathlib import Path

from traceproof.csharp_locations import validate_locations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--fixtures-root", type=Path)
    parser.add_argument("--framework-facts", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.input.resolve()
    rows = []
    for case in json.loads((root / "report.json").read_text()):
        if args.fixtures_root:
            case_name = case["profile"] + "-" + case["variant"]
            source = (args.fixtures_root / case["profile"] / case["variant"]).resolve()
            source.relative_to(args.fixtures_root.resolve())
        else:
            case_name = case["case"]["name"]
            source = (root / case_name / "source").resolve()
        for flow_id, flow in enumerate(case["result"]["paths"]):
            for step, node in enumerate(flow):
                path = (source / node["file"]).resolve(strict=True)
                path.relative_to(source)
                relative = str(path.relative_to(source))
                result = validate_locations(
                    path.read_bytes(),
                    case["source_sha256"][relative],
                    [node],
                    framework_facts=args.framework_facts,
                )
                rows.append(
                    {
                        "case": case_name,
                        "flow": flow_id,
                        "step": step,
                        "file": relative,
                        "validation": result,
                    }
                )
    with args.output.open("x") as f:
        json.dump(rows, f, indent=2)
    counts = {}
    for row in rows:
        result = row["validation"]
        status = result["nodes"][0]["status"] if result["nodes"] else result["status"]
        counts[status] = counts.get(status, 0) + 1
    print(counts)


if __name__ == "__main__":
    main()
