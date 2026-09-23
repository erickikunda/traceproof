import pytest

from veriflow import c_family_parser as parser

SOURCE = b"""#include <stdlib.h>
int main(int count, char **arguments) {
 char *command = arguments[1];
 system(command);
 return 0;
}
"""


@pytest.mark.parametrize("language", ["c", "cpp"])
def test_isolated_endpoints(language):
    result = parser.parse(SOURCE, language)
    assert result == parser.parse_isolated(SOURCE, language)
    assert result["sources"] == [{"line": 3, "code": "arguments[1]"}]
    assert result["sinks"] == [{"line": 4, "code": "system(command)", "argument_code": "command"}]
    renamed = SOURCE.replace(b"char **arguments", b"char *inputs[]").replace(
        b"arguments[1]", b"inputs[2]"
    )
    assert parser.parse(renamed, language)["sources"]


@pytest.mark.parametrize("language", ["c", "cpp"])
@pytest.mark.parametrize(
    "old,new,endpoint",
    [
        (b"main(", b"helper(", "sources"),
        (b"char **arguments", b"int **arguments", "sources"),
        (b"arguments[1]", b"arguments[0]", "sources"),
        (b"arguments[1]", b"arguments[count]", "sources"),
        (b"arguments[1]", b"arguments[-1]", "sources"),
        (b"arguments[1]", b"arguments[0x1]", "sources"),
        (b"char *command", b"arguments++; char *command", "sources"),
        (b"char *command", b"{ char **arguments; } char *command", "sources"),
        (b"<stdlib.h>", b"<stdio.h>", "sinks"),
        (b"int main", b"int system(char *);\nint main", "sinks"),
        (b"system(command)", b"system(command, 0)", "sinks"),
        (b"system(command)", b"object.system(command)", "sinks"),
    ],
)
def test_misleading_endpoints(language, old, new, endpoint):
    assert not parser.parse(SOURCE.replace(old, new), language)[endpoint]


@pytest.mark.parametrize("language", ["c", "cpp"])
def test_limits_and_preprocessing(language, monkeypatch):
    assert parser.parse(b"\xff", language)["status"] == "encoding_error"
    assert parser.parse(b"int main( {", language)["status"] == "syntax_error"
    assert (
        parser.parse(b"#define system other\n" + SOURCE, language)["status"]
        == "unsupported_preprocessing"
    )
    monkeypatch.setattr(parser, "MAX_BYTES", 1)
    assert parser.parse(SOURCE, language)["status"] == "size_limit"
    monkeypatch.setattr(parser, "MAX_BYTES", 1024)
    monkeypatch.setattr(parser, "MAX_NODES", 1)
    assert parser.parse(SOURCE, language)["status"] == "node_limit"


@pytest.mark.parametrize(
    "prefix", [b"namespace custom {}\n", b"class Other {};\n", b"template<class T> void f() {}\n"]
)
def test_cpp_context_withheld(prefix):
    assert parser.parse(prefix + SOURCE, "cpp")["status"] == "unsupported_cpp_context"
