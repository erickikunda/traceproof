"""Networked OSV acquisition then offline load; drives the pinned image from the host."""

import argparse
import json
import subprocess
import time
from pathlib import Path

HOST = "osv-vulnerabilities.storage.googleapis.com"
SOURCE = f"https://{HOST}"


def identity(tag):
    return json.loads(subprocess.check_output(["docker", "image", "inspect", tag]))[0]


def runtime(image, mounts, network, memory="4g"):
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
        "--read-only",
        "--user",
        "1000710000:0",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--cpus",
        "2",
        "--memory",
        memory,
        "--pids-limit",
        "512",
        "--tmpfs",
        "/work:rw,exec,nosuid,nodev,size=2g,mode=1777",
        "--tmpfs",
        "/tmp:rw,exec,nosuid,nodev,size=2g,mode=1777",
        *mounts,
        image,
    ]


def acquire(image, export, arguments, network="bridge", timeout=1800):
    mounts = ["--mount", f"type=bind,source={export},target=/export"]
    return subprocess.run(
        runtime(image, mounts, network) + arguments,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--ecosystem", action="append", default=None)
    # Emulated architectures need a far longer budget than a native run.
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    ecosystems = args.ecosystem or ["Go", "Maven"]
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    export = root / "export"
    export.mkdir()
    export.chmod(0o777)

    image = identity(args.image)
    assert image["Os"] == "linux", image["Os"]
    selection = [item for name in ecosystems for item in ("--ecosystem", name)]

    # No scanner toolchain, and the recorded application inputs are readable.
    check = subprocess.run(
        runtime(image["Id"], [], "none")[:-1]
        + [
            "--entrypoint",
            "/bin/bash",
            image["Id"],
            "-ec",
            "test ! -e /opt/joern-cli; test ! -e /opt/codeql-bundle; test ! -e /opt/jdk; "
            "cat /opt/traceproof/application-inputs.sha256",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert check.returncode == 0, check.stderr
    (root / "image-inputs.txt").write_text(check.stdout)

    # An unallowed host is refused, and nothing is written.
    denied = acquire(
        image["Id"],
        export,
        [
            "https://unapproved.invalid",
            "/export/denied",
            *selection,
            "--allowed-host",
            HOST,
            "--allow-unpinned",
        ],
        timeout=120,
    )
    assert denied.returncode == 1, denied.stdout
    assert not (export / "denied").exists(), "a refused acquisition created an output directory"

    # Unpinned acquisition requires the explicit opt-in.
    unpinned = acquire(
        image["Id"],
        export,
        [SOURCE, "/export/unpinned", *selection, "--allowed-host", HOST],
        timeout=120,
    )
    assert unpinned.returncode == 1, unpinned.stdout
    assert "opt-in" in unpinned.stderr, unpinned.stderr

    # A wrong pinned digest is refused; re-fetching by observed digest is not asserted
    # because the upstream export changes continuously.
    mismatch = acquire(
        image["Id"],
        export,
        [
            SOURCE,
            "/export/mismatch",
            "--ecosystem",
            ecosystems[0],
            "--allowed-host",
            HOST,
            f"--expected-sha256={ecosystems[0]}={'0' * 64}",
        ],
        timeout=900,
    )
    assert mismatch.returncode == 1, mismatch.stdout

    timings = {}
    started = time.monotonic()
    acquired = acquire(
        image["Id"],
        export,
        [SOURCE, "/export/osv", *selection, "--allowed-host", HOST, "--allow-unpinned"],
        timeout=args.timeout,
    )
    timings["acquire"] = time.monotonic() - started
    assert acquired.returncode == 0, acquired.stderr
    receipt = json.loads(acquired.stdout)
    profile = json.loads((export / "osv/osv-profile.json").read_text())
    assert receipt["record_count"] == profile["record_count"] > 0, receipt["record_count"]
    assert sorted(profile["ecosystems"]) == sorted(ecosystems), profile["ecosystems"]
    assert all(item["pinning"] == "observed_only" for item in receipt["archives"])
    assert receipt["model_calls"] == 0

    # The offline half must load the same export with networking disabled.
    started = time.monotonic()
    offline = subprocess.run(
        runtime(
            image["Id"], ["--mount", f"type=bind,source={export},target=/export,readonly"], "none"
        )[:-1]
        + [
            "--entrypoint",
            "python",
            image["Id"],
            "-c",
            "import json;from traceproof.osv_database import load_profile,build_index;"
            "p=load_profile('/export/osv/osv-profile.json');i,l=build_index(p);"
            "print(json.dumps({'packages':len(i),**l}))",
        ],
        capture_output=True,
        text=True,
        timeout=args.timeout,
        check=False,
    )
    timings["offline_load"] = time.monotonic() - started
    assert offline.returncode == 0, offline.stderr
    loading = json.loads(offline.stdout)
    assert loading["records_loaded"] > 0 and loading["packages"] > 0, loading

    report = {
        "state": "validated",
        "image": image["Id"],
        "ecosystems": profile["ecosystems"],
        "record_count": profile["record_count"],
        "duplicate_records_skipped": receipt["duplicate_records_skipped"],
        "expanded_bytes": receipt["expanded_bytes"],
        "inventory_sha256": profile["inventory_sha256"],
        "offline_load": loading,
        "elapsed_seconds": {name: round(value, 1) for name, value in timings.items()},
        "limitations": [
            "Freshness is the moment of acquisition; the upstream export changes continuously.",
            "Record counts reflect the live export and are not a fixed acceptance threshold.",
            "Acquisition establishes no vulnerability position and performs no matching.",
        ],
    }
    (root / "qualification.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
