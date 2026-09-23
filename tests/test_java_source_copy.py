import zipfile
from pathlib import Path

import pytest
from test_indexing import captured

from veriflow.codeql import extract
from veriflow.persistence import exclusive_worker


def test_source_only_copy_contains_no_build_files(store, archive, manifest, monkeypatch):
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("src/main/java/C.java", "class C {}")
        out.writestr("pom.xml", "untrusted build config")
        out.writestr("build.gradle", "untrusted build script")
        out.writestr("gradlew", "untrusted wrapper")
        out.writestr("lib/dep.jar", "untrusted jar")
    run = captured(store, archive, manifest)
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: None)
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


def test_csharp_copy_omits_project_and_binary_inputs(store, archive, manifest, monkeypatch):
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("C.cs", "class C {}")
        out.writestr("App.csproj", "untrusted build instructions")
        out.writestr("Directory.Build.targets", "untrusted targets")
        out.writestr("dep.dll", "untrusted binary")
        out.writestr("View.cshtml", "unqualified view")
    run = captured(store, archive, manifest)
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: None)
    with exclusive_worker(store.root):
        result = extract(store, run, language="auto", allow_csharp_downloads=True)
    root = Path(result["database_path"]).parent / "source"
    assert [p.name for p in root.iterdir()] == ["C.cs"]
    assert result["language"] == "csharp"
    assert result["language_scope"]["omitted_file_count"] == 4


def test_csharp_requires_explicit_download_opt_in(store, archive, manifest):
    import pytest

    from veriflow.domain import VeriFlowError

    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("C.cs", "class C {}")
    run = captured(store, archive, manifest)
    with (
        exclusive_worker(store.root),
        pytest.raises(VeriFlowError, match="allow-csharp-downloads"),
    ):
        extract(store, run, language="auto")
    assert not (store.root / "codeql").exists()


@pytest.mark.parametrize("language,extension", [("javascript", "js"), ("typescript", "ts")])
def test_js_ts_source_copy_omits_configuration_and_other_language(
    store, archive, manifest, monkeypatch, language, extension
):
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("app.js", "const x = 1;")
        out.writestr("app.ts", "const x: number = 1;")
        out.writestr("package.json", '{"scripts":{"prepare":"untrusted"}}')
        out.writestr("tsconfig.json", '{"extends":"untrusted"}')
        out.writestr("index.html", "<script>unqualified</script>")
    run = captured(store, archive, manifest)
    monkeypatch.setattr("veriflow.codeql.shutil.which", lambda _: None)
    with exclusive_worker(store.root):
        result = extract(store, run, language=language)
    root = Path(result["database_path"]).parent / "source"
    assert [p.name for p in root.iterdir()] == [f"app.{extension}"]
    assert result["language_scope"]["omitted_file_count"] == 4
