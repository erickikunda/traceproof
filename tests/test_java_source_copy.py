import zipfile
from pathlib import Path

from test_indexing import captured

from traceproof.codeql import extract
from traceproof.persistence import exclusive_worker


def test_source_only_copy_contains_no_build_files(store, archive, manifest, monkeypatch):
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("src/main/java/C.java", "class C {}")
        out.writestr("pom.xml", "untrusted build config")
        out.writestr("build.gradle", "untrusted build script")
        out.writestr("gradlew", "untrusted wrapper")
        out.writestr("lib/dep.jar", "untrusted jar")
    run = captured(store, archive, manifest)
    monkeypatch.setattr("traceproof.codeql.shutil.which", lambda _: None)
    with exclusive_worker(store.root):
        result = extract(store, run, language="auto", java_profile="source-only")
    root = Path(result["database_path"]).parent / "source"
    assert [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()] == [
        "src/main/java/C.java"
    ]
    assert (root / "src/main/java/C.java").read_text() == "class C {}"
    assert result["language_scope"]["omitted_file_count"] == 4
    assert result["language"] == "java"
    assert result["language_scope"]["language_selection"] == "automatic"
