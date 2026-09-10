"""Pinned operator-supplied SDK/reference inventory; no repository configuration trust."""

import hashlib
import json
from pathlib import Path, PurePosixPath

from traceproof.domain import TraceProofError

MAX_FILES = 20000


def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise TraceProofError("Dependency inventories cannot contain symlinks")
        if path.is_file():
            if len(result) >= MAX_FILES:
                raise TraceProofError("Dependency inventory exceeds file limit")
            with path.open("rb") as handle:
                result[path.relative_to(root).as_posix()] = hashlib.file_digest(
                    handle, "sha256"
                ).hexdigest()
    return result


def load_profile(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as handle:
        raw = handle.read(4 * 1024 * 1024 + 1)
    try:
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError()
        profile = json.loads(raw)
        if (
            set(profile) != {"version", "codeql_version", "sdk_version", "sdk", "references"}
            or profile["version"] != "1"
        ):
            raise ValueError()
        for field in ("codeql_version", "sdk_version"):
            if (
                not isinstance(profile[field], str)
                or not profile[field]
                or len(profile[field]) > 100
            ):
                raise ValueError()
        roots = {}
        for key in ("sdk", "references"):
            value = profile[key]
            if set(value) != {"directory", "files"} or not isinstance(value["directory"], str):
                raise ValueError()
            relative = PurePosixPath(value["directory"])
            if relative.is_absolute() or ".." in relative.parts or "\\" in value["directory"]:
                raise ValueError()
            root = (path.parent / relative).resolve(strict=True)
            if not root.is_relative_to(path.parent) or not root.is_dir():
                raise ValueError()
            if (
                not isinstance(value["files"], dict)
                or not value["files"]
                or len(value["files"]) > MAX_FILES
            ):
                raise ValueError()
            if inventory(root) != value["files"]:
                raise TraceProofError("Dependency profile integrity mismatch")
            roots[key] = root
        if not (roots["sdk"] / "dotnet").is_file() or not list(roots["references"].rglob("*.dll")):
            raise ValueError()
    except (ValueError, TypeError, KeyError, AttributeError):
        raise TraceProofError("Invalid C# dependency profile") from None
    return {
        "id": hashlib.sha256(raw).hexdigest(),
        "path": path,
        "sdk": roots["sdk"],
        "references": roots["references"],
        "codeql_version": profile["codeql_version"],
        "sdk_version": profile["sdk_version"],
        "file_count": sum(len(profile[key]["files"]) for key in ("sdk", "references")),
    }


def environment(profile, root):
    feed = root / "local-feed"
    feed.mkdir()
    # A trusted generated configuration replaces repository/user NuGet configuration.
    from xml.sax.saxutils import escape

    (root / "source" / "NuGet.Config").write_text(
        '<configuration><packageSources><clear/><add key="local" value="'
        + escape(str(feed), {'"': "&quot;"})
        + '"/></packageSources></configuration>'
    )
    return {
        "DOTNET_ROOT": str(profile["sdk"]),
        "DOTNET_CLI_HOME": str(root / "dotnet-home"),
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_NOLOGO": "1",
        "NUGET_PACKAGES": str(root / "packages"),
        "CODEQL_EXTRACTOR_CSHARP_BUILDLESS_DOTNET_FRAMEWORK_REFERENCES": str(profile["references"]),
        "CODEQL_EXTRACTOR_CSHARP_BUILDLESS_DOTNET_FRAMEWORK_REFERENCES_USE_SUBFOLDERS": "true",
        "CODEQL_EXTRACTOR_CSHARP_BUILDLESS_NUGET_FEEDS_CHECK": "false",
        "CODEQL_EXTRACTOR_CSHARP_BUILDLESS_NUGET_FEEDS_FALLBACK": feed.as_uri(),
        "CODEQL_EXTRACTOR_CSHARP_BUILDLESS_NUGET_FEEDS_FALLBACK_INCLUDE_NUGET_CONFIG_FEEDS": (
            "false"
        ),
        "CODEQL_EXTRACTOR_CSHARP_BUILDLESS_EXTRACT_WEB_VIEWS": "false",
        "CODEQL_EXTRACTOR_CSHARP_BUILDLESS_EXTRACT_RESOURCES": "false",
    }
