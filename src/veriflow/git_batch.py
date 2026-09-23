"""Bounded sequential Git-URL CSV acquisition; never scans or invokes models."""

import csv
import hashlib
import io
import json
import time
from pathlib import Path

from veriflow.domain import VeriFlowError
from veriflow.git_acquisition import acquire
from veriflow.git_credentials import read_credentials
from veriflow.git_transport import transport_settings

HEADERS = {"repo_id", "url", "revision", "owner", "classification"}


def checkpoint(output, summary, acquired_rows):
    # A consumer must inspect the terminal batch state; CSV contains successes only.
    if acquired_rows:
        temporary = output / "archives.csv.tmp"
        with temporary.open("w", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=list(acquired_rows[0]))
            writer.writeheader()
            writer.writerows(acquired_rows)
        temporary.replace(output / "archives.csv")
    temporary = output / "acquisition-batch.json.tmp"
    temporary.write_text(json.dumps(summary, indent=2))
    temporary.replace(output / "acquisition-batch.json")


def acquire_csv(
    manifest,
    output,
    allowed_hosts,
    max_rows=10,
    timeout=900,
    *,
    ca_bundle=None,
    proxy=None,
    credential_file=None,
):
    read_credentials(credential_file)
    transport_settings(ca_bundle, proxy)
    if not 1 <= max_rows <= 10 or not 1 <= timeout <= 3600 or not allowed_hosts:
        raise VeriFlowError("Require allowed hosts, 1–10 rows and 1–3600 seconds")
    with Path(manifest).open("rb") as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise VeriFlowError("Git CSV exceeds 1 MiB")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        if (
            not reader.fieldnames
            or len(reader.fieldnames) != len(HEADERS)
            or set(reader.fieldnames) != HEADERS
        ):
            raise VeriFlowError("Git CSV requires repo_id,url,revision,owner,classification only")
        rows = list(reader)
    except (UnicodeError, csv.Error):
        raise VeriFlowError("Git CSV must be well-formed UTF-8") from None
    if not 1 <= len(rows) <= max_rows:
        raise VeriFlowError("Git CSV is empty or exceeds requested batch limit")
    output = Path(output).absolute()
    try:
        output.mkdir(mode=0o700)
    except FileExistsError:
        raise VeriFlowError("Acquisition output already exists; choose a new directory") from None
    summary = dict(
        schema_version="1",
        state="running",
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
        total_rows=len(rows),
        model_calls=0,
        scans_started=0,
        items=[dict(row_number=i + 2, state="pending") for i in range(len(rows))],
    )
    acquired_rows = []
    deadline = time.monotonic() + timeout
    checkpoint(output, summary, acquired_rows)
    try:
        for index, row in enumerate(rows):
            entry = summary["items"][index]
            remaining = int(deadline - time.monotonic())
            if remaining < 1:
                for pending in summary["items"][index:]:
                    pending.update(state="not_started", reason="batch_deadline")
                break
            entry["state"] = "acquiring"
            checkpoint(output, summary, acquired_rows)
            directory = output / f"row-{index + 2:06d}"
            try:
                if None in row or any(value is None for value in row.values()):
                    raise VeriFlowError("CSV record field count does not match header")
                receipt = acquire(
                    row["url"],
                    row["revision"],
                    allowed_hosts,
                    directory,
                    row["repo_id"],
                    row["owner"],
                    row["classification"],
                    timeout=min(300, remaining),
                    **({"credential_file": credential_file} if credential_file else {}),
                    **({"ca_bundle": ca_bundle, "proxy": proxy} if ca_bundle or proxy else {}),
                )
                with (directory / "input.csv").open() as source:
                    ready = list(csv.DictReader(source))
                if len(ready) != 1:
                    raise VeriFlowError("Acquisition did not emit exactly one archive record")
                acquired_rows.append(ready[0])
                entry.update(
                    state="acquired",
                    repo_id=receipt["repo_id"],
                    resolved_commit=receipt["resolved_commit"],
                    archive_sha256=receipt["archive_sha256"],
                    acquisition_directory=directory.name,
                )
            except VeriFlowError as exc:
                entry.update(state="failed", error=str(exc))
            checkpoint(output, summary, acquired_rows)
        summary["state"] = (
            "acquired" if all(i["state"] == "acquired" for i in summary["items"]) else "incomplete"
        )
        return summary
    except Exception as exc:
        summary.update(state="failed", error_type=type(exc).__name__)
        raise
    finally:
        summary["acquired_rows"] = len(acquired_rows)
        summary["archive_manifest"] = "archives.csv" if acquired_rows else None
        checkpoint(output, summary, acquired_rows)
