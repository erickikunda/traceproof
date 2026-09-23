"""Pinned local Maven artifacts for the qualified CodeQL standalone adapter."""

import csv
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from veriflow.csharp_dependencies import inventory
from veriflow.domain import VeriFlowError


def load_java_profile(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as handle:
        raw = handle.read(4 * 1024 * 1024 + 1)
    try:
        data = json.loads(raw)
        if len(raw) > 4 * 1024 * 1024 or set(data) != {
            "version",
            "codeql_version",
            "repository",
            "artifacts",
        }:
            raise ValueError()
        # The classpath CSV is a version-specific extractor interface.
        if data["version"] != "1" or data["codeql_version"] != "2.27.0":
            raise ValueError()
        repo = data["repository"]
        if set(repo) != {"directory", "files"} or not isinstance(repo["directory"], str):
            raise ValueError()
        rel = PurePosixPath(repo["directory"])
        if rel.is_absolute() or ".." in rel.parts or "\\" in str(rel):
            raise ValueError()
        root = (path.parent / rel).resolve(strict=True)
        if not root.is_relative_to(path.parent) or not root.is_dir():
            raise ValueError()
        artifacts = data["artifacts"]
        if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 1000:
            raise ValueError()
        if any(not isinstance(a, str) for a in artifacts) or len(set(artifacts)) != len(artifacts):
            raise ValueError()
        expected = set()
        for artifact in artifacts:
            if not re.fullmatch(
                r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*:[A-Za-z0-9_-]+:jar:[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*",
                artifact,
            ):
                raise ValueError()
            group, name, _, version = artifact.split(":")
            expected.add(f"{group.replace('.', '/')}/{name}/{version}/{name}-{version}.jar")
        if not isinstance(repo["files"], dict) or set(repo["files"]) != expected:
            raise ValueError()
        if inventory(root) != repo["files"]:
            raise VeriFlowError("Java dependency profile integrity mismatch")
    except (ValueError, TypeError, KeyError, AttributeError):
        raise VeriFlowError("Invalid Java dependency profile") from None
    return dict(
        id=hashlib.sha256(raw).hexdigest(),
        path=path,
        repository=root,
        artifacts=artifacts,
        codeql_version=data["codeql_version"],
        file_count=len(expected),
    )


def java_environment(profile, root):
    classpath = root / "java-classpath.csv"
    with classpath.open("w", newline="") as handle:
        writer = csv.writer(handle)
        for artifact in profile["artifacts"]:
            writer.writerow([artifact, "veriflow-local", profile["repository"].as_uri()])
    return {
        "CODEQL_JAVA_EXTRACTOR_STANDALONE_CLASSPATH_FILE": str(classpath),
        "CODEQL_EXTRACTOR_JAVA_OPTION_BUILDLESS_DEPENDENCY_DIR": str(
            root / "java-dependency-cache"
        ),
    }
