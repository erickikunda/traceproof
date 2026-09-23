import pytest

from veriflow.joern_flask import endpoints, parse_isolated

BASE = (
    b"from flask import request\nimport requests\n"
    b'u = request.args.get("u")\nrequests.get(u, timeout=5)\n'
)


def test_http_endpoints_and_isolation():
    result = endpoints(BASE, http_urls=True)
    assert result["sources"] == [{"line": 3, "name": "get"}]
    assert result["sinks"] == [{"line": 4, "name": "get"}]
    assert parse_isolated(BASE, http_urls=True) == result
    assert endpoints(BASE)["sinks"] == []
    assert endpoints(
        BASE.replace(b"import requests", b"import requests as r").replace(
            b"requests.get", b"r.get"
        ),
        http_urls=True,
    )["sinks"]


@pytest.mark.parametrize(
    "change",
    [b"import other as requests", b"import requests\nrequests = other", b"from other import *"],
)
def test_shadowed_http_client(change):
    assert endpoints(BASE.replace(b"import requests", change), http_urls=True)["sinks"] == []


@pytest.mark.parametrize(
    "call",
    [
        b"requests.get(url=u)",
        b"requests.get(u, **options)",
        b"requests.post(u)",
        b"requests.get(u, timeout=value)",
    ],
)
def test_unqualified_call_shapes(call):
    assert (
        endpoints(BASE.replace(b"requests.get(u, timeout=5)", call), http_urls=True)["sinks"] == []
    )
