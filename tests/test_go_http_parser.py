from pathlib import Path

import pytest

from veriflow.go_http_parser import parse, parse_isolated

BASE = (Path(__file__).parent / "fixtures/joern-go-http/vulnerable/main.go").read_bytes()


def test_isolated_parser_and_aliases():
    for name in ["vulnerable", "renamed"]:
        source = (Path(__file__).parent / "fixtures/joern-go-http" / name / "main.go").read_bytes()
        result = parse_isolated(source)
        assert result == parse(source)
        assert len(result["sources"]) == len(result["sinks"]) == 1
        assert result["sinks"][0]["argument_code"] == "value"


@pytest.mark.parametrize(
    "before,after,kind",
    [
        (b'"net/http"', b'"example.com/fake"', "sources"),
        (b"*http.Request", b"*other.Request", "sources"),
        (b"*http.Request", b"http.Request", "sources"),
        (b"value :=", b"r = other; value :=", "sources"),
        (b"value :=", b"r := other; value :=", "sources"),
        (b"value :=", b"http := other; value :=", "sources"),
        (b"value :=", b"for r = range values {} ; value :=", "sources"),
        (b'FormValue("command")', b"FormValue(key)", "sources"),
        (b'FormValue("command")', b'FormValue("command", "extra")', "sources"),
        (b'"os/exec"', b'"example.com/fake"', "sinks"),
        (b"value :=", b"exec := other; value :=", "sinks"),
        (b'"sh", "-c"', b'"printf", "%s"', "sinks"),
        (b'"sh", "-c"', b'shell, "-c"', "sinks"),
        (b'"sh", "-c"', b'"sh", flag', "sinks"),
        (b'"-c", value', b'"-c", value, extra', "sinks"),
        (b'"-c", value', b'"-c", values...', "sinks"),
        (b"exec.Command", b"other.Command", "sinks"),
        (b'exec.Command("sh", "-c", value).Run()', b'println("exec.Command")', "sinks"),
    ],
)
def test_misleading_and_unsupported_endpoints(before, after, kind):
    assert parse(BASE.replace(before, after))[kind] == []


def test_bounds_and_bad_input(monkeypatch):
    assert parse(b"\xff")["status"] == "encoding_error"
    assert parse(b"package (")["status"] == "syntax_error"
    assert (
        parse(BASE.replace(b'import "net/http"', b'import . "net/http"'))["status"] == "dot_import"
    )
    assert parse(b"x" * (1024 * 1024 + 1))["status"] == "size_limit"
    monkeypatch.setattr("veriflow.go_http_parser.MAX_NODES", 2)
    assert parse(BASE)["status"] == "node_limit"


def test_raw_imports_cannot_bypass_binding_inventory():
    source = BASE.replace(b'import "net/http"', b'import "net/http"; import http `other/http`')
    assert parse(source)["status"] == "unsupported_import"
