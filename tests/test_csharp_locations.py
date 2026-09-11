import hashlib

from traceproof.csharp_locations import MAX_SOURCE_BYTES, validate_locations


def check(source, nodes, digest=None):
    data = source.encode()
    return validate_locations(data, digest or hashlib.sha256(data).hexdigest(), nodes)


def test_direct_and_preceding_line_are_not_blanket_adjusted():
    source = "class C {\n void M(string name) {\n  Use(name);\n }\n}"
    rows = check(source, [{"line": 1, "code": "string name"}, {"line": 3, "code": "name"}])["nodes"]
    assert [r["span"]["line"] for r in rows] == [2, 3]
    assert [r["span"]["line_delta"] for r in rows] == [1, 0]
    assert rows[0]["raw"]["line"] == 1


def test_repeated_identifier_on_same_or_adjacent_lines_is_ambiguous():
    for body in ["Use(name, name);", "Use(name);\n Use(name);"]:
        rows = check("class C { void M() {\n " + body + "\n}}", [{"line": 2, "code": "name"}])[
            "nodes"
        ]
        assert rows[0]["status"] == "ambiguous"
        assert rows[0]["span"] is None


def test_multiline_unicode_crlf_offsets():
    source = 'class C {\r\n void M(string name) {\r\n var q = "é" +\r\n name;\r\n }}'
    code = '"é" +\r\n name'
    row = check(source, [{"line": 2, "code": code}])["nodes"][0]
    span = row["span"]
    assert (span["line"], span["end_line"]) == (3, 4)
    assert source.encode()[span["start_byte"] : span["end_byte"]].decode() == code


def test_comments_strings_and_faraway_matches_are_rejected():
    source = 'class C { void M() {\n // name\n var s = "name";\n\n Use(name);\n }}'
    for line in [1, 2, 3]:
        assert (
            check(source, [{"line": line, "code": "name"}])["nodes"][0]["status"] == "unsupported"
        )


def test_hash_syntax_encoding_and_size_fail_closed():
    assert check("class C {}", [], "wrong")["status"] == "source_mismatch"
    assert check("class {", [])["status"] == "syntax_error"
    assert validate_locations(b"\xff", "", [])["status"] == "invalid_input"
    assert validate_locations(b"x" * (MAX_SOURCE_BYTES + 1), "", [])["status"] == "limit"


def test_invalid_coordinates_and_empty_code():
    nodes = [
        {"line": True, "code": "C"},
        {"line": -1, "code": "C"},
        {"line": 999, "code": "C"},
        {"line": 1, "code": ""},
    ]
    assert all(r["status"] == "unsupported" for r in check("class C {}", nodes)["nodes"])
