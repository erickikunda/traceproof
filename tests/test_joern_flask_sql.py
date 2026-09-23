import pytest

from veriflow.joern_flask import endpoints, parse_isolated

BASE = (
    b"from flask import request\nimport sqlite3\n"
    b'q = request.args.get("q")\nsqlite3.connect(":memory:").execute(q)\n'
)


def test_sql_text_endpoint():
    result = endpoints(BASE, sql_queries=True)
    assert result["sinks"] == [{"line": 4, "name": "execute"}]
    assert parse_isolated(BASE, sql_queries=True) == result
    assert endpoints(BASE)["sinks"] == []


@pytest.mark.parametrize(
    "replacement", [b"import other as sqlite3", b"import sqlite3\nsqlite3 = other"]
)
def test_foreign_connection_not_selected(replacement):
    assert endpoints(BASE.replace(b"import sqlite3", replacement), sql_queries=True)["sinks"] == []


def test_cursor_and_keyword_are_not_qualified():
    for call in (b"cursor.execute(q)", b'sqlite3.connect(":memory:").execute(sql=q)'):
        source = BASE.replace(b'sqlite3.connect(":memory:").execute(q)', call)
        assert endpoints(source, sql_queries=True)["sinks"] == []
