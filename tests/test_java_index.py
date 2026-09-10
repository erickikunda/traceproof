import zipfile

import pytest
from test_indexing import captured

from traceproof.java_index import build_java_index, parse_isolated
from traceproof.java_parser import MAX_BYTES, parse
from traceproof.persistence import exclusive_worker


def test_declarations_and_calls_ignore_comments_and_strings():
    result = parse(b"""class Outer {
        // void fake() { dangerous(); }
        String text = "executeQuery()";
        int run() { return service.lookup(); }
        record Item(int id) {}
    }""")
    assert result["status"] == "parsed"
    assert [s["name"] for s in result["symbols"]] == [
        "<file>.Outer",
        "<file>.Outer.run",
        "<file>.Outer.Item",
    ]
    assert len(result["calls"]) == 1
    assert result["calls"][0]["expression"] == "lookup"
    assert result["calls"][0]["resolution"] == "unresolved"


@pytest.mark.parametrize(
    "source,status",
    [
        (b"class Bad { void x( }", "syntax_error"),
        (b"\xff", "encoding_error"),
        (b" " * (MAX_BYTES + 1), "size_limit"),
    ],
)
def test_invalid_or_oversized_source_has_no_facts(source, status):
    assert parse(source) == {"status": status, "symbols": [], "calls": []}


def test_isolated_parser():
    assert parse_isolated(b"class Good {} ")["status"] == "parsed"


def test_snapshot_index_reuse_and_failed_file_coverage(store, archive, manifest, monkeypatch):
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("Good.java", "class Good { void run() {} }")
        out.writestr("Bad.java", "class Bad {")
    run = captured(store, archive, manifest)
    with exclusive_worker(store.root):
        result = build_java_index(store, run)
        assert result["syntax_gate"] == "blocked"
        assert result["java_files"] == 2 and result["parsed_java_files"] == 1
        assert result["semantic_resolution"] == "not_qualified"
        monkeypatch.setattr(
            "traceproof.java_index.parse_isolated", lambda _: pytest.fail("reparsed")
        )
        assert build_java_index(store, run) == result


def test_runner_blocks_invalid_java_before_extraction(
    store, archive, manifest, tmp_path, monkeypatch
):
    from traceproof.pipeline import scan_run

    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("Bad.java", "class Bad {")
    run = captured(store, archive, manifest)
    query = tmp_path / "query.ql"
    query.write_text("// test query")
    monkeypatch.setattr("traceproof.pipeline.extract", lambda *a, **k: pytest.fail("extracted"))
    result = scan_run(store, run, query, language="java")
    assert result["status"] == "blocked"
    assert result["java_syntax_index"]["files"][0]["status"] == "syntax_error"
    assert result["extraction_id"] is None and result["model_calls"] == 0
