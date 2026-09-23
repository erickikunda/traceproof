import io
import stat
import tarfile
import zipfile

import pytest
from conftest import row

from veriflow.artifacts import ArtifactStore
from veriflow.domain import ArchiveLimits, IntakeSpec, TraceProofError


@pytest.mark.parametrize("kind", ["zip", "tar", "tar.gz"])
def test_formats_pin_source_and_preserve_layout(tmp_path, kind):
    archive = tmp_path / f"source.{kind}"
    if kind == "zip":
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr("nested/app.py", "original")
    else:
        with tarfile.open(archive, "w:gz" if kind == "tar.gz" else "w") as out:
            item = tarfile.TarInfo("nested/app.py")
            item.size = len(b"original")
            out.addfile(item, io.BytesIO(b"original"))
    store = ArtifactStore(tmp_path / "state")
    manifest = store.capture(IntakeSpec(**row(archive)), tmp_path)
    archive.write_bytes(b"changed later")
    assert manifest.files[0].path == "nested/app.py"
    assert store.verify(manifest.snapshot_id) == manifest
    assert (store.path(manifest.snapshot_id) / "tree/nested/app.py").read_text() == "original"


@pytest.mark.parametrize(
    "names",
    [
        ["../escape.py"],
        ["/escape.py"],
        ["a/../../escape.py"],
        ["a\\escape.py"],
        ["C:/escape.py"],
        ["a/./file.py"],
        ["same.py", "same.py"],
        ["Name.py", "name.py"],
        ["Caf\u00e9/a.py", "Cafe\u0301/b.py"],
        ["A/a.py", "a/b.py"],
        ["a.py", "a.py/b.py"],
    ],
)
def test_unsafe_zip_paths_rejected(tmp_path, names):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as out:
        for name in names:
            out.writestr(name, b"x")
    store = ArtifactStore(tmp_path / "state")
    with pytest.raises(TraceProofError):
        store.capture(IntakeSpec(**row(archive)), tmp_path)
    assert list(store.root.iterdir()) == []
    assert not (tmp_path / "escape.py").exists()


@pytest.mark.parametrize(
    "kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE]
)
def test_tar_special_entries_rejected(tmp_path, kind):
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as out:
        item = tarfile.TarInfo("link")
        item.type = kind
        item.linkname = "../../escape"
        out.addfile(item)
    with pytest.raises(TraceProofError, match="links and special"):
        ArtifactStore(tmp_path / "state").capture(IntakeSpec(**row(archive)), tmp_path)


def test_zip_symlink_rejected(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as out:
        item = zipfile.ZipInfo("link")
        item.create_system = 3
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        out.writestr(item, "../../escape")
    with pytest.raises(TraceProofError, match="links and special"):
        ArtifactStore(tmp_path / "state").capture(IntakeSpec(**row(archive)), tmp_path)


@pytest.mark.parametrize(
    "limits",
    [
        ArchiveLimits(max_archive_bytes=10),
        ArchiveLimits(max_expanded_bytes=10),
        ArchiveLimits(max_members=1),
        ArchiveLimits(max_path_depth=1),
        ArchiveLimits(max_path_bytes=4),
    ],
)
def test_resource_limits(archive, tmp_path, limits):
    with pytest.raises(TraceProofError, match="limit"):
        ArtifactStore(tmp_path / "state", limits).capture(
            IntakeSpec(**row(archive)), archive.parent
        )


def test_ratio_limit(tmp_path):
    archive = tmp_path / "ratio.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as out:
        out.writestr("file.txt", "a" * 100_000)
    with pytest.raises(TraceProofError, match="ratio"):
        ArtifactStore(tmp_path / "state", ArchiveLimits(max_compression_ratio=2)).capture(
            IntakeSpec(**row(archive)), tmp_path
        )


@pytest.mark.parametrize("tamper", ["content", "extra", "missing", "archive"])
def test_integrity_verification_catches_tampering(tmp_path, archive, tamper):
    store = ArtifactStore(tmp_path / "state")
    manifest = store.capture(IntakeSpec(**row(archive)), archive.parent)
    root = store.path(manifest.snapshot_id)
    target = root / "tree/project/app.py"
    if tamper == "content":
        target.chmod(0o600)
        target.write_text("changed")
    elif tamper == "extra":
        (root / "tree/extra.py").write_text("added")
    elif tamper == "missing":
        target.unlink()
    else:
        target = root / "source.archive"
        target.chmod(0o600)
        target.write_bytes(b"changed")
    with pytest.raises(TraceProofError):
        store.verify(manifest.snapshot_id)


def test_nested_archives_not_unpacked(tmp_path):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as out:
        out.writestr("../evil.py", "x")
    archive = tmp_path / "outer.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("inner.zip", inner.getvalue())
    manifest = ArtifactStore(tmp_path / "state").capture(IntakeSpec(**row(archive)), tmp_path)
    assert [f.path for f in manifest.files] == ["inner.zip"]


@pytest.mark.parametrize("name", [" trailing.py", "folder /a.py"])
def test_whitespace_path_cannot_diverge_from_manifest(tmp_path, name):
    archive = tmp_path / "spaces.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr(name, "x")
    with pytest.raises(TraceProofError, match="ambiguous"):
        ArtifactStore(tmp_path / "state").capture(IntakeSpec(**row(archive)), tmp_path)


@pytest.mark.parametrize("mutation", ["null", "encrypted", "unsupported-compression"])
def test_malformed_zip_metadata(tmp_path, mutation):
    import struct

    archive = tmp_path / "metadata.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("fileX.py", "x")
    data = bytearray(archive.read_bytes())
    central = data.index(b"PK\x01\x02")
    if mutation == "null":
        data = data.replace(b"fileX.py", b"file\x00.py")
    elif mutation == "encrypted":
        struct.pack_into("<H", data, 6, 1)
        struct.pack_into("<H", data, central + 8, 1)
    else:
        struct.pack_into("<H", data, 8, 99)
        struct.pack_into("<H", data, central + 10, 99)
    archive.write_bytes(data)
    with pytest.raises(TraceProofError):
        ArtifactStore(tmp_path / "state").capture(IntakeSpec(**row(archive)), tmp_path)


def test_oversized_tar_metadata_rejected_before_read(tmp_path):
    archive = tmp_path / "metadata.tar"
    item = tarfile.TarInfo("pax")
    item.type, item.size = tarfile.XHDTYPE, 65537
    archive.write_bytes(item.tobuf())
    with pytest.raises(TraceProofError, match="metadata"):
        ArtifactStore(tmp_path / "state").capture(IntakeSpec(**row(archive)), tmp_path)
