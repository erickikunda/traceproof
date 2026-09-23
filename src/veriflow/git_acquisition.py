"""Bounded credential-free HTTPS Git acquisition, separate from offline scan execution."""

import csv
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from pydantic import ValidationError

from veriflow.domain import IntakeSpec, TraceProofError
from veriflow.git_credentials import credential_environment, read_credentials
from veriflow.git_transport import configure, transport_settings

MAX_FILES = 2000
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_WORK_BYTES = 256 * 1024 * 1024


def validate_remote(url, revision, allowed_hosts):
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        raise TraceProofError("Invalid Git URL") from None
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
        or parsed.path == "/"
        or any(c.isspace() or ord(c) < 32 for c in url)
        or "%" in url
        or "\\" in url
        or not url.isascii()
        or host.lower() not in {h.lower() for h in allowed_hosts}
    ):
        raise TraceProofError("Git requires credential-free HTTPS on an explicitly allowed host")
    if (
        not (
            re.fullmatch(r"[a-f0-9]{40}", revision)
            or re.fullmatch(r"refs/(heads|tags)/[A-Za-z0-9][A-Za-z0-9._/-]{0,180}", revision)
        )
        or ".." in revision
        or "//" in revision
        or revision.endswith(("/", ".", ".lock"))
    ):
        raise TraceProofError("Use a full refs/heads or refs/tags name, or a 40-character commit")


def work_bytes(root):
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink())


class Git:
    def __init__(self, root, timeout):
        executable = shutil.which("git")
        if not executable:
            raise TraceProofError("Git executable not found")
        self.root = root
        self.deadline = time.monotonic() + timeout
        self.command = [
            executable,
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "credential.helper=",
            "-c",
            "protocol.allow=never",
            "-c",
            "protocol.https.allow=always",
            "-c",
            "http.followRedirects=false",
            "-c",
            "http.sslVerify=true",
            "-c",
            "fetch.fsckObjects=true",
            "-c",
            "fetch.unpackLimit=0",
            "-c",
            "gc.auto=0",
            "-c",
            "maintenance.auto=false",
        ]
        self.env = {
            "PATH": os.defpath,
            "HOME": str(root),
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_LFS_SKIP_SMUDGE": "1",
        }

    def call(self, *args, limit=MAX_FILE_BYTES):
        # Disk monitoring is a soft cap; OS/container quotas remain required for hard limits.
        with tempfile.TemporaryFile(dir=self.root) as output:
            process = subprocess.Popen(
                self.command + list(args),
                cwd=self.root,
                env=self.env | (getattr(self, "auth_env", {}) if "fetch" in args else {}),
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            try:
                while True:
                    status = process.poll()
                    if (
                        time.monotonic() > self.deadline
                        or output.tell() > limit
                        or work_bytes(self.root) > MAX_WORK_BYTES
                    ):
                        raise TraceProofError("Git acquisition exceeded time or storage limit")
                    if status is not None:
                        break
                    time.sleep(0.05)
                if status:
                    raise TraceProofError(
                        "Git command failed; check repository, revision and connectivity"
                    )
                output.seek(0)
                data = output.read(limit + 1)
                if len(data) > limit:
                    raise TraceProofError("Git output exceeds limit")
                return data
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def acquire(
    url,
    revision,
    allowed_hosts,
    output,
    repo_id,
    owner,
    classification,
    timeout=300,
    *,
    ca_bundle=None,
    proxy=None,
    credential_file=None,
):
    settings = transport_settings(ca_bundle, proxy)
    validate_remote(url, revision, allowed_hosts)
    auth_env = credential_environment(read_credentials(credential_file), url)
    if not 1 <= timeout <= 900:
        raise TraceProofError("Acquisition timeout must be 1–900 seconds")
    output = Path(output).absolute()
    try:
        spec = IntakeSpec(
            repo_id=repo_id,
            source_type="pvc",
            source_uri=str(output / "source.zip"),
            owner=owner,
            classification=classification,
        )
    except ValidationError:
        raise TraceProofError("Invalid acquisition repository metadata") from None
    try:
        output.mkdir(mode=0o700)  # Exclusive ownership; never replace earlier acquisitions.
    except FileExistsError:
        raise TraceProofError("Acquisition output already exists; choose a new directory") from None
    receipt = {
        "schema_version": "1",
        "state": "failed",
        "url": url,
        "requested_revision": revision,
        "repo_id": repo_id,
        "model_calls": 0,
        "coverage_verified": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix=".git-acquire-", dir=output) as directory:
            root = Path(directory)
            git = Git(root, timeout)
            configure(git, settings)
            git.auth_env = auth_env
            version = git.call("--version").decode().strip()
            git.call("init", "--bare", "--template=", "repo.git")
            # No clone/local optimizations, checkout, submodule recursion or remote helpers.
            git.call(
                "--git-dir=repo.git",
                "fetch",
                "--depth=1",
                "--no-tags",
                "--no-recurse-submodules",
                "--",
                url,
                revision,
            )
            commit = (
                git.call("--git-dir=repo.git", "rev-parse", "--verify", "FETCH_HEAD^{commit}")
                .decode()
                .strip()
            )
            if not re.fullmatch(r"[a-f0-9]{40}", commit):
                raise TraceProofError(
                    "Only SHA-1-format Git repositories are supported in this slice"
                )
            if re.fullmatch(r"[a-f0-9]{40}", revision) and commit != revision:
                raise TraceProofError("Fetched commit differs from the requested commit")
            tree = git.call("--git-dir=repo.git", "ls-tree", "-r", "-z", "-l", commit)
            entries = [row for row in tree.split(b"\0") if row]
            if not entries or len(entries) > MAX_FILES:
                raise TraceProofError("Empty repository or source file count exceeds limit")
            files, total, names = [], 0, set()
            archive_path = root / "source.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
                for row in entries:
                    metadata, raw_path = row.split(b"\t", 1)
                    mode, kind, oid, size = metadata.split()
                    path = raw_path.decode("utf-8")
                    parts = PurePosixPath(path).parts
                    if (
                        mode not in (b"100644", b"100755")
                        or kind != b"blob"
                        or not parts
                        or path.startswith("/")
                        or ".." in parts
                        or ".git" in {p.lower() for p in parts}
                        or "\\" in path
                        or any(ord(c) < 32 for c in path)
                        or path.casefold() in names
                    ):
                        raise TraceProofError(
                            "Unsupported source path, symlink, submodule or collision"
                        )
                    names.add(path.casefold())
                    count = int(size)
                    total += count
                    if count > MAX_FILE_BYTES or total > MAX_SOURCE_BYTES:
                        raise TraceProofError("Source content exceeds acquisition limits")
                    blob = git.call(
                        "--git-dir=repo.git", "cat-file", "blob", oid.decode(), limit=MAX_FILE_BYTES
                    )
                    if len(blob) != count:
                        raise TraceProofError("Git blob size mismatch")
                    if blob.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                        raise TraceProofError("Git LFS content retrieval is not supported")
                    # Raw blobs preserve export-ignore/export-subst files and bypass filters.
                    archive.writestr(path, blob)
                    files.append(
                        {
                            "path": path,
                            "git_blob": oid.decode(),
                            "size_bytes": count,
                            "sha256": hashlib.sha256(blob).hexdigest(),
                        }
                    )
            with archive_path.open("rb") as source:
                sha = hashlib.file_digest(source, "sha256").hexdigest()
            shutil.move(archive_path, output / "source.zip")
            receipt.update(
                state="acquired",
                resolved_commit=commit,
                git_version=version,
                archive_sha256=sha,
                files=files,
                source_bytes=total,
                omissions=[],
                limitations=[
                    "Submodules, symlinks and LFS are rejected",
                    "No inherited credentials/proxy/CA config or redirect support",
                    "Remote history is not authenticated by this receipt",
                ],
            )
        receipt_bytes = json.dumps(receipt, indent=2).encode()
        with (output / "input.csv").open("w", newline="") as target:
            row = spec.model_dump(exclude={"acquisition_data"}) | {
                "sha256": sha,
                "acquisition_receipt": str(output / "acquisition.json"),
                "acquisition_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            }
            writer = csv.DictWriter(target, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        return receipt
    except Exception as exc:
        for name in ("source.zip", "input.csv"):
            (output / name).unlink(missing_ok=True)
        receipt.update(state="failed", error_type=type(exc).__name__)
        if isinstance(exc, TraceProofError):
            raise
        raise TraceProofError("Git acquisition failed; no scan input published") from None
    finally:
        (output / "acquisition.json").write_text(json.dumps(receipt, indent=2))
