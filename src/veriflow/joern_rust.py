"""Restricted dependency-free Cargo preparation for the experimental Rust profile."""

import json
import tomllib
from pathlib import Path

from veriflow.domain import VeriFlowError


def cargo_manifest(tree, manifest):
    """Reject unsupported Cargo inputs; generate only the admitted binary metadata."""
    records = {f.path: f for f in manifest.files}
    if "Cargo.toml" not in records:
        raise VeriFlowError("Rust requires a root Cargo.toml")
    raw = (tree / "Cargo.toml").read_bytes()
    if len(raw) > 65536:
        raise VeriFlowError("Cargo manifest exceeds profile limit")
    try:
        doc = tomllib.loads(raw.decode())
        if set(doc) != {"package", "bin"}:
            raise ValueError()
        package = doc["package"]
        if set(package) - {"name", "version", "edition", "build"}:
            raise ValueError()
        if package.get("build", False) is not False:
            raise ValueError()
        for key in ("name", "version", "edition"):
            if not isinstance(package[key], str):
                raise ValueError()
        if package["edition"] not in {"2015", "2018", "2021", "2024"}:
            raise ValueError()
        bins = doc["bin"]
        if not isinstance(bins, list) or len(bins) != 1 or set(bins[0]) != {"name", "path"}:
            raise ValueError()
        binary = bins[0]
        if not all(isinstance(v, str) for v in binary.values()):
            raise ValueError()
        path = Path(binary["path"])
        if path.is_absolute() or ".." in path.parts or path.suffix != ".rs":
            raise ValueError()
        if path.as_posix() not in records:
            raise ValueError()
        lines = ["[package]"] + [
            f"{k} = {json.dumps(package[k])}" for k in ("name", "version", "edition")
        ]
        lines += [
            "build = false",
            "autobins = false",
            "autolib = false",
            "autoexamples = false",
            "autotests = false",
            "autobenches = false",
            "",
            "[[bin]]",
        ]
        lines += [f"{k} = {json.dumps(binary[k])}" for k in ("name", "path")]
        return ("\n".join(lines) + "\n").encode()
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise VeriFlowError(
            "Rust requires one explicit binary; dependencies/workspaces/build hooks unsupported"
        ) from None


def trusted_toolchain(store, root):
    if root is None:
        raise VeriFlowError("Rust requires an operator-supplied toolchain directory")
    root = Path(root).resolve(strict=True)
    if any(root.is_relative_to(store.root / d) for d in ("artifacts", "scans")):
        raise VeriFlowError("Rust toolchain must not come from scan artifacts")
    if not all(
        (root / p).is_file()
        for p in ("bin/rustc", "bin/cargo", "lib/rustlib/src/rust/library/core/src/lib.rs")
    ):
        raise VeriFlowError("Rust toolchain requires rustc, cargo and rust-src")
    return root
