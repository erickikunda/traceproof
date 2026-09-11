from pathlib import Path

import pytest

from traceproof.rust_env_parser import parse, parse_isolated

BASE = (Path(__file__).parent / "fixtures/joern-rust-env/vulnerable/main.rs").read_bytes()
ALIASED = (Path(__file__).parent / "fixtures/joern-rust-env/renamed/main.rs").read_bytes()


def test_isolated_parser_and_aliases():
    for source in (BASE, ALIASED):
        parsed = parse_isolated(source)
        assert parsed == parse(source)
        assert len(parsed["sources"]) == len(parsed["sinks"]) == 1
        assert '.arg("-c").arg(' in parsed["sinks"][0]["code"]


@pytest.mark.parametrize(
    "before,after,kind",
    [
        (b"std::env::var", b"other::env::var", "sources"),
        (b'"TRACEPROOF_COMMAND"', b"key", "sources"),
        (b'"TRACEPROOF_COMMAND"', b'r"TRACEPROOF_COMMAND"', "sources"),
        (b'"TRACEPROOF_COMMAND"', b'"key", "extra"', "sources"),
        (b"std::process::Command", b"other::Command", "sinks"),
        (b'new("sh")', b'new("printf")', "sinks"),
        (b'new("sh")', b"new(shell)", "sinks"),
        (b'arg("-c")', b"arg(flag)", "sinks"),
        (b"arg(command)", b"arg(command, extra)", "sinks"),
        (b'arg("-c").arg(command)', b'args(["-c", command])', "sinks"),
        (b'arg("-c").arg(command)', b'arg("-c").env("X", "Y").arg(command)', "sinks"),
    ],
)
def test_unsupported_endpoint_shapes(before, after, kind):
    assert parse(BASE.replace(before, after))[kind] == []


@pytest.mark.parametrize(
    "extra",
    [
        b"mod std {}",
        b"fn std() {}",
        b"use other as std;",
        b'#[cfg(feature="other")]',
        b"macro_rules! x { () => {} }",
        b'println!("x");',
        b"use std::env::*;",
        b"use std::{env, process};",
    ],
)
def test_unsupported_context_withheld(extra):
    result = parse(extra + b"\n" + BASE)
    assert not result["sources"] and not result["sinks"]


@pytest.mark.parametrize(
    "before,after,kind",
    [
        (b"fn main() {", b"fn main() { let read_setting = other;", "sources"),
        (b"fn main() {", b"fn main() { struct Process;", "sinks"),
        (b"use std::env::var", b"use other::env::var", "sources"),
        (b"use std::process::Command", b"use other::Command", "sinks"),
    ],
)
def test_alias_binding_checks(before, after, kind):
    assert parse(ALIASED.replace(before, after))[kind] == []


def test_bounds_and_invalid_input(monkeypatch):
    assert parse(b"\xff")["status"] == "encoding_error"
    assert parse(b"fn (")["status"] == "syntax_error"
    assert parse(b"x" * (1024 * 1024 + 1))["status"] == "size_limit"
    monkeypatch.setattr("traceproof.rust_env_parser.MAX_NODES", 2)
    assert parse(BASE)["status"] == "node_limit"
