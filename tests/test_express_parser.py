from pathlib import Path

import pytest

from traceproof.express_parser import parse, parse_isolated

BASE = (Path(__file__).parent / "fixtures/joern-express/javascript/vulnerable/app.js").read_bytes()


@pytest.mark.parametrize("language", ["javascript", "typescript"])
def test_endpoints_and_isolated_parser_agree(language):
    result = parse_isolated(BASE, language)
    assert result == parse(BASE, language)
    assert result["sources"] == [{"line": 4, "code": "incoming.query.code"}]
    assert result["sinks"] == [{"line": 5, "code": "eval(term)", "argument_code": "term"}]


@pytest.mark.parametrize("language", ["javascript", "typescript"])
@pytest.mark.parametrize(
    "before,after,kind",
    [
        (b'from "express"', b'from "other"', "sources"),
        (b"const app = express();", b"const app = other();", "sources"),
        (b"app.get(", b"other.get(", "sources"),
        (b"incoming.query.code", b'incoming["query"].code', "sources"),
        (b"incoming.query.code", b"incoming?.query.code", "sources"),
        (b"const term", b"incoming = other; const term", "sources"),
        (b"const term", b"const incoming = other; const term", "sources"),
        (b"const term", b"function nested(incoming) {} const term", "sources"),
        (b"const term", b"app.get = other; const term", "sources"),
        (b"const term", b"const eval = other; const term", "sinks"),
        (b"const term", b"eval = other; const term", "sinks"),
        (b"const term", b"globalThis.eval = other; const term", "sinks"),
        (b"eval(term)", b"object.eval(term)", "sinks"),
        (b"eval(term)", b"eval?.(term)", "sinks"),
        (b"eval(term)", b"eval(term, term)", "sinks"),
        (b"eval(term)", b'"eval(term)"', "sinks"),
    ],
)
def test_unsupported_or_misleading_endpoints_withheld(language, before, after, kind):
    assert parse(BASE.replace(before, after), language)[kind] == []


def test_typescript_annotations():
    source = BASE.replace(b"(incoming, response)", b"(incoming: Request, response: Response)")
    result = parse(source, "typescript")
    assert len(result["sources"]) == len(result["sinks"]) == 1
    assert parse(source, "javascript")["status"] == "syntax_error"


def test_parser_bounds_and_bad_input(monkeypatch):
    assert parse(b"\xff", "javascript")["status"] == "encoding_error"
    assert parse(b"const (", "typescript")["status"] == "syntax_error"
    assert parse(BASE, "other")["status"] == "unsupported_language"
    assert parse(b"x" * (1024 * 1024 + 1), "javascript")["status"] == "size_limit"
    monkeypatch.setattr("traceproof.express_parser.MAX_NODES", 2)
    assert parse(BASE, "javascript")["status"] == "node_limit"
