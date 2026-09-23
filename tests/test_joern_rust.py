import tomllib
from types import SimpleNamespace

import pytest
from test_slice03 import captured_source as captured_source

from veriflow.domain import TraceProofError
from veriflow.joern_rust import cargo_manifest, trusted_toolchain

BASE = (
    '[package]\nname="probe"\nversion="0.1.0"\nedition="2021"\n'
    '[[bin]]\nname="probe"\npath="main.rs"\n'
)


def fixture(tmp_path, text):
    (tmp_path / "Cargo.toml").write_text(text)
    return SimpleNamespace(files=[SimpleNamespace(path=p) for p in ("Cargo.toml", "main.rs")])


def test_generated_manifest_disables_implicit_execution(tmp_path):
    manifest = fixture(tmp_path, BASE)
    result = tomllib.loads(cargo_manifest(tmp_path, manifest).decode())
    for key in ("build", "autobins", "autolib", "autoexamples", "autotests", "autobenches"):
        assert result["package"][key] is False
    assert result["bin"] == [{"name": "probe", "path": "main.rs"}]
    assert (tmp_path / "Cargo.toml").read_text() == BASE


@pytest.mark.parametrize(
    "text",
    [
        BASE + '[dependencies]\nevil="1"\n',
        BASE + '[workspace]\nmembers=["other"]\n',
        BASE.replace("[package]", '[package]\nbuild="custom.rs"'),
        BASE.replace("[package]", "[package]\nbuild=true"),
        BASE.replace("main.rs", "../main.rs"),
        BASE.replace("main.rs", "/main.rs"),
        BASE.replace("main.rs", "missing.rs"),
        BASE + '[[bin]]\nname="extra"\npath="main.rs"\n',
        BASE.replace('edition="2021"', "edition={workspace=true}"),
        "not TOML",
    ],
)
def test_unsupported_cargo_rejected(tmp_path, text):
    with pytest.raises(TraceProofError):
        cargo_manifest(tmp_path, fixture(tmp_path, text))


def test_rust_toolchain_required(store):
    with pytest.raises(TraceProofError):
        trusted_toolchain(store, None)


@pytest.mark.parametrize("represented", [True, False])
def test_durable_rust_rejects_empty_graph(
    store, captured_source, tmp_path, monkeypatch, represented
):
    import json

    from veriflow import joern, joern_rust
    from veriflow.scanning import scan_report

    run = captured_source({"Cargo.toml": BASE, "main.rs": "fn main() {}\n"})
    home = tmp_path / "tool"
    (home / "lib").mkdir(parents=True)
    (home / "lib" / f"io.joern.joern-cli-{joern.VERSION}.jar").touch()
    monkeypatch.setattr(joern_rust, "trusted_toolchain", lambda *a: tmp_path)

    def fake(command, root, name, timeout, **options):
        assert options["rust_home"] == tmp_path
        prepared = tomllib.loads((root / "source/Cargo.toml").read_text())
        assert prepared["package"]["build"] is False
        if name == "analyze":
            (root / "flows.json").write_text(
                json.dumps(
                    {
                        "schema_version": "2",
                        "engine_id": "joern",
                        "rule_id": "veriflow/joern-rust-lookup-arg-v1",
                        "represented_rust_files": ["main.rs"] if represented else [],
                        "source_count": 0,
                        "sink_count": 0,
                        "flow_count": 0,
                        "paths": [],
                    }
                )
            )

    monkeypatch.setattr(joern, "stage", fake)
    report = joern.discover(store, run, home, language="rust", rust_home=tmp_path)
    fetched = scan_report(store, "example", run, report["attempt_id"])
    assert fetched["status"] == ("partial" if represented else "failed")
    assert fetched["candidate_count"] == (0 if represented else None)
