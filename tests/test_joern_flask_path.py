from traceproof.joern_flask import endpoints, parse_isolated


def test_file_sink_and_legacy_separation():
    code = b'from flask import request\nname = request.args.get("name")\nopen(name)\n'
    assert endpoints(code, file_paths=True)["sinks"] == [{"line": 3, "name": "open"}]
    assert endpoints(code)["sinks"] == []
    assert parse_isolated(code, file_paths=True)["sinks"] == [{"line": 3, "name": "open"}]


def test_shadows_and_unsupported_modes():
    for code in [
        b"def f(open, name):\n    open(name)",
        b"from other import open\nopen(name)",
        b'open(name, "w")',
        b"open(file=name)",
        b"open(*args)",
    ]:
        assert endpoints(code, file_paths=True)["sinks"] == []
