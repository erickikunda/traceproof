"""Restricted Linux qualification of the experimental C# frontend and syntax evidence."""

import json
import subprocess
import sys
from pathlib import Path

root = Path("/opt/veriflow")
work = Path("/work/acceptance")
work.mkdir()
common = [
    "--joern-home",
    "/opt/joern-cli",
    "--experimental-classpath",
    str(root / "csharp-repair/patched-classpath.txt"),
]
results = []
for script, name in [
    ("validate_joern_csharp.py", "baseline"),
    ("validate_joern_csharp_binding.py", "binding"),
]:
    subprocess.run(
        [sys.executable, str(root / "scripts" / script), *common, "--output", str(work / name)],
        check=True,
    )
    rows = json.loads((work / name / "report.json").read_text())
    results.extend(rows)
    Path("/reports", name + "-results.json").write_text(json.dumps(rows, indent=2))
subprocess.run(
    [
        sys.executable,
        str(root / "scripts/validate_csharp_locations.py"),
        "--input",
        str(work / "baseline"),
        "--fixtures-root",
        str(root / "tests/fixtures"),
        "--framework-facts",
        "--output",
        str(work / "framework.json"),
    ],
    check=True,
)
audit = json.loads((work / "framework.json").read_text())
assert len(audit) == 18
for row in audit:
    assert row["validation"]["status"] == "parsed"
    assert row["validation"]["nodes"][0]["status"] == "validated_span"
facts = [fact for row in audit for fact in row["validation"]["nodes"][0].get("framework_facts", [])]
assert sum(f["category"] == "sinks" for f in facts) == 5
assert sum(f["category"] == "sources" for f in facts) == 7
Path("/reports/framework.json").write_text(json.dumps(audit, indent=2))
Path("/reports/build-receipt.json").write_bytes(
    (root / "csharp-repair/build-receipt.json").read_bytes()
)
subprocess.run(
    [
        sys.executable,
        str(root / "scripts/validate_joern_csharp_discovery.py"),
        "--joern-home",
        "/opt/joern-cli",
        "--repair-dir",
        str(root / "csharp-repair"),
        "--output",
        str(work / "durable"),
    ],
    check=True,
)
durable = json.loads((work / "durable/case-results.json").read_text())
assert len(durable) == 2
results.extend(dict(row, profile="durable-discovery") for row in durable)
for artifact in (work / "durable").iterdir():
    if artifact.suffix in {".json", ".html"}:
        Path("/reports", "durable-" + artifact.name).write_bytes(artifact.read_bytes())
Path("/reports/case-results.json").write_text(json.dumps(results, indent=2))
