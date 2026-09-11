import hashlib
from pathlib import Path

from traceproof.csharp_locations import validate_locations
from traceproof.csharp_parser import parse


def facts(source, nodes, digest=None):
    data = source.encode()
    return validate_locations(
        data, digest or hashlib.sha256(data).hexdigest(), nodes, framework_facts=True
    )


def test_attributed_parameter_joins_by_bytes_not_same_line():
    source = (
        "using Microsoft.AspNetCore.Mvc;\n"
        "class C { void M([FromQuery] string name, string other) {} }"
    )
    rows = facts(source, [{"line": 1, "code": "string name"}, {"line": 1, "code": "string other"}])[
        "nodes"
    ]
    assert rows[0]["span"]["syntax_kind"] == "parameter_type_and_name"
    assert rows[0]["framework_facts"][0]["fact"] == "explicit_from_query_parameter"
    assert rows[1]["framework_facts"] == []


def test_repeated_source_stays_ambiguous_and_gets_no_facts():
    source = (
        "using Microsoft.AspNetCore.Mvc;\n"
        "class C { void M([FromQuery] string name) {} void N(string name) {} }"
    )
    row = facts(source, [{"line": 2, "code": "string name"}])["nodes"][0]
    assert row["status"] == "ambiguous"
    assert row["framework_facts"] == []


def test_sink_only_attaches_inside_rhs():
    source = 'class C { void M() { command.CommandText = "SELECT " + name; } }'
    rows = facts(source, [{"line": 1, "code": '"SELECT " + name'}, {"line": 1, "code": "command"}])[
        "nodes"
    ]
    assert rows[0]["framework_facts"][0]["fact"] == "command_text_rhs_syntax"
    assert rows[1]["framework_facts"] == []


def test_classic_fixtures_and_existing_parser_contract():
    for profile in ("csharp-mvc", "csharp-webapi"):
        source = Path(f"tests/fixtures/{profile}/vulnerable/LookupController.cs").read_text()
        original = parse(source.encode())
        assert original["sources"] and all(
            set(s) == {"line", "end_line"} for s in original["sources"]
        )
        result = facts(source, [{"line": original["sources"][0]["line"], "code": "name"}])
        assert result["nodes"][0]["framework_facts"][0]["fact"] == "classic_http_get_parameter"


def test_alias_and_local_attribute_lookalike_withhold_facts():
    for prefix in (
        "using X = Microsoft.AspNetCore.Mvc.FromQueryAttribute;\n",
        "class FromQueryAttribute {}\n",
    ):
        source = (
            prefix
            + "using Microsoft.AspNetCore.Mvc;\nclass C { void M([FromQuery] string name) {} }"
        )
        result = facts(source, [{"line": 3, "code": "string name"}])
        assert result["framework_status"] == "unsupported_context"
        assert result["nodes"][0]["framework_facts"] == []


def test_changed_hash_withholds_all_facts():
    assert facts("class C {}", [], "wrong")["status"] == "source_mismatch"
