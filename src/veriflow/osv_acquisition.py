"""Bounded OSV export acquisition on an allowed host; the network adapter stays separate."""

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from veriflow.bundles import canonical
from veriflow.domain import VeriFlowError
from veriflow.intake import now
from veriflow.osv_database import OSV_ECOSYSTEMS

MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
MAX_RECORD_BYTES = 2 * 1024 * 1024
# Matches the loader; a full npm export alone carries over 229,000 advisories.
MAX_RECORDS = 500_000
MAX_COMPRESSION_RATIO = 200
MAX_NAME_BYTES = 255


class ExportReader(Protocol):
    def fetch(self, url: str, max_bytes: int) -> bytes: ...


def validate_source(base_url, allowed_hosts):
    """Credential-free HTTPS on an explicitly allowed host; no inherited configuration."""
    try:
        parsed = urlsplit(base_url)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        raise VeriFlowError("Invalid OSV source URL") from None
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or any(c.isspace() or ord(c) < 32 for c in base_url)
        or not base_url.isascii()
        or any(c in base_url for c in "%\\")
        or ".." in parsed.path
        or host.lower() not in {allowed.lower() for allowed in allowed_hosts}
    ):
        raise VeriFlowError("OSV acquisition requires credential-free HTTPS on an allowed host")
    return base_url.rstrip("/")


def validate_ecosystems(ecosystems):
    if not ecosystems or not set(ecosystems) <= set(OSV_ECOSYSTEMS.values()):
        raise VeriFlowError("OSV acquisition requires ecosystems TraceProof can evaluate")
    return sorted(set(ecosystems))


def member_name(info):
    """Records are flat JSON files; an unexpected member shape aborts the whole acquisition."""
    name = info.filename
    if (
        info.is_dir()
        or "/" in name
        or "\\" in name
        or not name.endswith(".json")
        or not name.isascii()
        or len(name.encode()) > MAX_NAME_BYTES
        or name.startswith(".")
        or (info.external_attr >> 16) & 0o170000 not in (0, 0o100000)
    ):
        raise VeriFlowError("OSV archive member is not a plain flat JSON record")
    return name


def expand(raw, destination, written, totals):
    """Refuse rather than skip: a silently incomplete database would later read as evaluated."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for info in archive.infolist():
                name = member_name(info)
                if info.file_size > MAX_RECORD_BYTES:
                    raise VeriFlowError("OSV record exceeds the per-record byte limit")
                totals["expanded"] += info.file_size
                if totals["expanded"] > MAX_EXPANDED_BYTES:
                    raise VeriFlowError("OSV archive exceeds the expanded byte limit")
                if info.compress_size and (
                    info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
                ):
                    raise VeriFlowError("OSV archive member compression ratio is not accepted")
                with archive.open(info) as handle:
                    body = handle.read(MAX_RECORD_BYTES + 1)
                if len(body) != info.file_size or len(body) > MAX_RECORD_BYTES:
                    raise VeriFlowError("OSV record size does not match its archive entry")
                digest = hashlib.sha256(body).hexdigest()
                if name in written:
                    # The same advisory ships in several ecosystem archives.
                    if written[name] != digest:
                        raise VeriFlowError("OSV archives disagree about a record's contents")
                    totals["duplicates"] += 1
                    continue
                if len(written) >= MAX_RECORDS:
                    raise VeriFlowError("OSV export exceeds the record limit")
                path = destination / name
                with path.open("xb") as target:
                    target.write(body)
                    target.flush()
                    os.fsync(target.fileno())
                path.chmod(0o400)
                written[name] = digest
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise VeriFlowError(f"OSV archive expansion failed ({type(exc).__name__})") from exc


def acquire_osv(
    reader,
    *,
    base_url,
    ecosystems,
    allowed_hosts,
    output,
    expected_sha256=None,
    allow_unpinned=False,
    max_bytes=MAX_ARCHIVE_BYTES,
):
    """Fetch, expand and pin an OSV export; matching itself never touches the network."""
    source = validate_source(base_url, allowed_hosts)
    selected = validate_ecosystems(ecosystems)
    expected = expected_sha256 or {}
    if not isinstance(expected, dict) or not set(expected) <= set(selected):
        raise VeriFlowError("Expected digests must name selected ecosystems")
    missing = [name for name in selected if name not in expected]
    if missing and not allow_unpinned:
        raise VeriFlowError(
            "Unpinned OSV acquisition requires an explicit opt-in; supply digests or allow it"
        )
    if not 1 <= max_bytes <= MAX_ARCHIVE_BYTES:
        raise VeriFlowError("OSV archive limit must be positive and bounded")
    output = Path(output).absolute()
    records = output / "records"
    try:
        # Refuse an existing directory: leftover records would enter the pinned inventory.
        output.mkdir(parents=True)
        records.mkdir()
    except OSError:
        raise VeriFlowError("OSV output directory must not already exist") from None
    written, totals, archives = {}, {"expanded": 0, "duplicates": 0}, []
    for ecosystem in selected:
        url = f"{source}/{ecosystem}/all.zip"
        raw = reader.fetch(url, max_bytes)
        if not isinstance(raw, bytes) or not raw or len(raw) > max_bytes:
            raise VeriFlowError("OSV archive response is empty or exceeds the byte limit")
        digest = hashlib.sha256(raw).hexdigest()
        if ecosystem in expected and digest != expected[ecosystem]:
            raise VeriFlowError("OSV archive SHA-256 does not match the expected digest")
        before = len(written)
        expand(raw, records, written, totals)
        archives.append(
            {
                "ecosystem": ecosystem,
                "url": url,
                "archive_sha256": digest,
                "archive_bytes": len(raw),
                "records_written": len(written) - before,
                "pinning": "operator_pinned" if ecosystem in expected else "observed_only",
            }
        )
    listing = dict(sorted(written.items()))
    profile = {
        "version": "1",
        "source": source,
        "exported_at": now(),
        "ecosystems": selected,
        "records_directory": "records",
        "record_count": len(listing),
        "inventory_sha256": hashlib.sha256(canonical(listing)).hexdigest(),
    }
    receipt = {
        "schema_version": "1",
        "kind": "osv",
        "state": "acquired",
        "acquired_at": profile["exported_at"],
        "source": source,
        "archives": archives,
        "record_count": len(listing),
        "duplicate_records_skipped": totals["duplicates"],
        "expanded_bytes": totals["expanded"],
        "inventory_sha256": profile["inventory_sha256"],
        "model_calls": 0,
        "limitations": [
            "Freshness is the moment of acquisition; the upstream export changes continuously.",
            "Only requested ecosystems were fetched; others are absent, not empty.",
            "Observed-only archives were not checked against an operator-approved digest.",
            "Acquisition establishes no vulnerability position and performs no matching.",
        ],
    }
    for name, content in (("osv-profile.json", profile), ("osv-acquisition-receipt.json", receipt)):
        path = output / name
        with path.open("x") as handle:
            json.dump(content, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        path.chmod(0o400)
    return {"profile": str(output / "osv-profile.json"), **receipt}
