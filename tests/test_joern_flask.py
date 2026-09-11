import pytest

from traceproof.joern_flask import endpoints, parse_isolated

BASE = b'from flask import request\nimport os\ndef run():\n    os.system(request.args.get("q"))\n'


def test_endpoints_and_isolated_parser_agree():
    result = parse_isolated(BASE)
    assert result == endpoints(BASE)
    assert result["sources"] == [{"line": 4, "name": "get"}]
    assert result["sinks"] == [{"line": 4, "name": "system"}]


@pytest.mark.parametrize(
    "source,kind",
    [
        (BASE.replace(b"def run():", b"def run(request):"), "sources"),
        (BASE.replace(b"import os", b"import os\nos.system = other"), "sinks"),
        (BASE.replace(b"from flask import request", b"from other import request"), "sources"),
        (BASE + b"from other import *\n", "sources"),
        (BASE.replace(b"def run():", b"def run(os):"), "sinks"),
        (BASE.replace(b'get("q")', b"get(key)"), "sources"),
        (BASE.replace(b'get("q")', b'get("q", "default")'), "sources"),
        (b"broken (", "sources"),
    ],
)
def test_unsupported_bindings_and_shapes_withheld(source, kind):
    assert endpoints(source)[kind] == []


def test_aliases_and_form_sources():
    source = BASE.replace(b"from flask import request", b"from flask import request as r")
    source = source.replace(b"request.args", b"r.form").replace(
        b"import os", b"import os as process"
    )
    source = source.replace(b"os.system", b"process.system")
    result = endpoints(source)
    assert len(result["sources"]) == len(result["sinks"]) == 1
