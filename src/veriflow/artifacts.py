"""Bounded archive intake; never delegate filesystem writes to archive extractall."""

import gzip
import hashlib
import json
import os
import shutil
import stat
import tarfile
import tempfile
import unicodedata
import zipfile
import zlib
from pathlib import Path
from typing import BinaryIO

from veriflow.domain import (
    ArchiveLimits,
    FileRecord,
    IntakeSpec,
    SnapshotManifest,
    VeriFlowError,
)

CHUNK = 1024 * 1024


class BoundedTarInfo(tarfile.TarInfo):
    @classmethod
    def frombuf(cls, buf, encoding, errors):
        info = super().frombuf(buf, encoding, errors)
        metadata_types = (
            tarfile.XHDTYPE,
            tarfile.XGLTYPE,
            tarfile.GNUTYPE_LONGNAME,
            tarfile.GNUTYPE_LONGLINK,
        )
        if info.type in metadata_types and info.size > 65536:
            raise VeriFlowError("Archive metadata exceeds 64 KiB limit")
        return info


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def digest_file(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def open_scoped_source(source_uri: str, input_root: Path) -> BinaryIO:
    """Walk with directory descriptors: no symlink or parent-swap escape."""
    root = input_root.resolve(strict=True)
    path = Path(source_uri)
    if ".." in path.parts:
        raise VeriFlowError("Source path contains parent traversal")
    try:
        parts = path.relative_to(root).parts
    except ValueError as exc:
        raise VeriFlowError("Source is outside the configured input root") from exc
    if not parts:
        raise VeriFlowError("Source must name an archive file")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise VeriFlowError("Source must be a regular file")
        return os.fdopen(fd, "rb")
    finally:
        os.close(directory)


class LimitedReader:
    """Bound decoded TAR bytes and oversized metadata reads before allocating."""

    def __init__(self, source: BinaryIO, limit: int):
        self.source = source
        self.remaining = limit

    def read(self, size: int = -1) -> bytes:
        if size < 0 or size > CHUNK:
            raise VeriFlowError("Oversized archive metadata read")
        block = self.source.read(min(size, self.remaining + 1))
        self.remaining -= len(block)
        if self.remaining < 0:
            raise VeriFlowError("Decoded archive exceeds stream limit")
        return block


class Extractor:
    def __init__(self, root: Path, limits: ArchiveLimits, archive_size: int):
        self.root, self.limits, self.archive_size = root, limits, archive_size
        self.members = 0
        self.total_bytes = 0
        self.explicit: set[str] = set()
        self.spellings: dict[str, str] = {}
        self.files: list[FileRecord] = []

    def member(self, name: str, directory: bool) -> Path | None:
        self.members += 1
        if self.members > self.limits.max_members:
            raise VeriFlowError("Archive member count exceeds limit")
        while name.startswith("./"):
            name = name[2:]
        name = name.rstrip("/") if directory else name
        if not name and directory:
            return None
        if (
            not name
            or name.startswith("/")
            or "\\" in name
            or ":" in name
            or any(ord(c) < 32 or ord(c) == 127 for c in name)
        ):
            raise VeriFlowError("Unsafe archive member path")
        parts = name.split("/")
        if any(part in ("", ".", "..") or part.strip() != part for part in parts):
            raise VeriFlowError("Archive member contains traversal or ambiguous components")
        if (
            len(parts) > self.limits.max_path_depth
            or len(name.encode()) > self.limits.max_path_bytes
        ):
            raise VeriFlowError("Archive member path exceeds limit")
        if name in self.explicit:
            raise VeriFlowError("Duplicate archive member path")
        self.explicit.add(name)
        for length in range(1, len(parts) + 1):
            prefix = "/".join(parts[:length])
            key = unicodedata.normalize("NFC", prefix).casefold()
            if key in self.spellings and self.spellings[key] != prefix:
                raise VeriFlowError("Case or Unicode collision in archive")
            self.spellings[key] = prefix
        target = self.root.joinpath(*parts)
        if directory:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def file(self, target: Path, source: BinaryIO, declared_size: int) -> None:
        if declared_size < 0 or self.total_bytes + declared_size > self.limits.max_expanded_bytes:
            raise VeriFlowError("Expanded archive exceeds limit")
        digest = hashlib.sha256()
        count = 0
        with target.open("xb") as destination:
            while block := source.read(CHUNK):
                count += len(block)
                self.total_bytes += len(block)
                if count > declared_size or self.total_bytes > self.limits.max_expanded_bytes:
                    raise VeriFlowError("Expanded archive exceeds declared size or limit")
                if self.total_bytes > self.archive_size * self.limits.max_compression_ratio:
                    raise VeriFlowError("Archive compression ratio exceeds limit")
                digest.update(block)
                destination.write(block)
            destination.flush()
            os.fsync(destination.fileno())
        if count != declared_size:
            raise VeriFlowError("Truncated archive member")
        self.files.append(
            FileRecord(
                path=target.relative_to(self.root).as_posix(),
                size_bytes=count,
                sha256=digest.hexdigest(),
            )
        )

    def extract(self, archive: Path) -> tuple[FileRecord, ...]:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as opened:
                if len(opened.infolist()) > self.limits.max_members:
                    raise VeriFlowError("Archive member count exceeds limit")
                for item in opened.infolist():
                    if item.orig_filename != item.filename:
                        raise VeriFlowError("Ambiguous ZIP member name")
                    mode = item.external_attr >> 16
                    file_type = stat.S_IFMT(mode)
                    if item.flag_bits & 1:
                        raise VeriFlowError("Encrypted archives are unsupported")
                    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                        raise VeriFlowError("Archive links and special files are forbidden")
                    if file_type == stat.S_IFDIR and not item.is_dir():
                        raise VeriFlowError("Inconsistent ZIP directory metadata")
                    target = self.member(item.filename, item.is_dir())
                    if target is not None and not item.is_dir():
                        with opened.open(item) as source:
                            self.file(target, source, item.file_size)
        else:
            with archive.open("rb") as raw:
                magic = raw.read(2)
                raw.seek(0)
                source = gzip.GzipFile(fileobj=raw) if magic == b"\x1f\x8b" else raw
                try:
                    # Includes headers/padding, not only file payload. Nested archives are data.
                    limit = self.limits.max_expanded_bytes + self.limits.max_members * 2048
                    reader = LimitedReader(source, limit)
                    with tarfile.open(fileobj=reader, mode="r|", tarinfo=BoundedTarInfo) as opened:
                        for item in opened:
                            if not item.isfile() and not item.isdir():
                                raise VeriFlowError(
                                    "Archive links and special files are forbidden"
                                )
                            if item.sparse is not None:
                                raise VeriFlowError("Sparse archive members are unsupported")
                            target = self.member(item.name, item.isdir())
                            if target is not None and item.isfile():
                                stream = opened.extractfile(item)
                                if stream is None:
                                    raise VeriFlowError("Archive member cannot be read")
                                with stream:
                                    self.file(target, stream, item.size)
                finally:
                    if source is not raw:
                        source.close()
        if not self.files:
            raise VeriFlowError("Archive contains no regular files")
        return tuple(sorted(self.files, key=lambda record: record.path))


class ArtifactStore:
    def __init__(self, state_root: Path, limits: ArchiveLimits | None = None):
        self.root = state_root / "artifacts"
        self.limits = limits or ArchiveLimits()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, snapshot_id: str) -> Path:
        if len(snapshot_id) != 64 or any(c not in "0123456789abcdef" for c in snapshot_id):
            raise VeriFlowError("Invalid snapshot ID")
        return self.root / snapshot_id

    def capture(self, spec: IntakeSpec, input_root: Path) -> SnapshotManifest:
        stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=self.root))
        try:
            archive = stage / "source.archive"
            with open_scoped_source(spec.source_uri, input_root) as source:
                before = os.fstat(source.fileno())
                if before.st_size > self.limits.max_archive_bytes:
                    raise VeriFlowError("Archive exceeds compressed byte limit")
                count = 0
                digest = hashlib.sha256()
                with archive.open("xb") as target:
                    while block := source.read(CHUNK):
                        count += len(block)
                        if count > self.limits.max_archive_bytes:
                            raise VeriFlowError("Archive exceeds compressed byte limit")
                        digest.update(block)
                        target.write(block)
                    target.flush()
                    os.fsync(target.fileno())
                after = os.fstat(source.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                ):
                    raise VeriFlowError(
                        "Source changed while being copied; submit a stable archive"
                    )
            archive_digest = digest.hexdigest()
            if spec.sha256 is not None and archive_digest != spec.sha256:
                raise VeriFlowError("Archive SHA-256 does not match expected digest")
            identity = json.dumps(["1", spec.repo_id, spec.classification, archive_digest])
            snapshot_id = hashlib.sha256(identity.encode()).hexdigest()
            final = self.path(snapshot_id)
            if final.exists():
                # Verify old artifacts instead of trusting an existing directory name.
                return self.verify(snapshot_id)
            tree = stage / "tree"
            tree.mkdir()
            records = Extractor(tree, self.limits, count).extract(archive)
            manifest = SnapshotManifest(
                snapshot_id=snapshot_id,
                repo_id=spec.repo_id,
                classification=spec.classification,
                archive_sha256=archive_digest,
                archive_size_bytes=count,
                files=records,
            )
            with (stage / "manifest.json").open("x") as out:
                out.write(manifest.model_dump_json(indent=2))
                out.flush()
                os.fsync(out.fileno())
            # Application-level immutability; not a sandbox against the owning OS user.
            for file in stage.rglob("*"):
                if file.is_file():
                    file.chmod(0o400)
            for directory in sorted(
                (path for path in stage.rglob("*") if path.is_dir()),
                key=lambda path: len(path.parts),
                reverse=True,
            ):
                sync_directory(directory)
            sync_directory(stage)
            os.rename(stage, final)
            sync_directory(self.root)
            return manifest
        except (
            OSError,
            tarfile.TarError,
            zipfile.BadZipFile,
            EOFError,
            ValueError,
            NotImplementedError,
            zlib.error,
        ) as exc:
            raise VeriFlowError(f"Archive intake failed ({type(exc).__name__})") from exc
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def verify(self, snapshot_id: str) -> SnapshotManifest:
        root = self.path(snapshot_id)
        try:
            if root.is_symlink() or (root / "tree").is_symlink():
                raise VeriFlowError("Snapshot root cannot be a symbolic link")
            manifest = SnapshotManifest.model_validate_json((root / "manifest.json").read_text())
            identity = json.dumps(
                ["1", manifest.repo_id, manifest.classification, manifest.archive_sha256]
            )
            if (
                manifest.snapshot_id != snapshot_id
                or hashlib.sha256(identity.encode()).hexdigest() != snapshot_id
            ):
                raise VeriFlowError("Snapshot identity mismatch")
            archive = root / "source.archive"
            if archive.is_symlink() or archive.stat().st_size != manifest.archive_size_bytes:
                raise VeriFlowError("Snapshot archive size/type mismatch")
            if digest_file(archive) != manifest.archive_sha256:
                raise VeriFlowError("Snapshot archive digest mismatch")
            actual = set()
            for path in (root / "tree").rglob("*"):
                if path.is_symlink():
                    raise VeriFlowError("Snapshot contains a symbolic link")
                if path.is_file():
                    actual.add(path.relative_to(root / "tree").as_posix())
            if actual != {record.path for record in manifest.files}:
                raise VeriFlowError("Snapshot inventory mismatch")
            for record in manifest.files:
                path = root / "tree" / record.path
                if path.stat().st_size != record.size_bytes or digest_file(path) != record.sha256:
                    raise VeriFlowError("Snapshot source digest mismatch")
            return manifest
        except (OSError, ValueError) as exc:
            raise VeriFlowError("Snapshot missing or manifest invalid") from exc
