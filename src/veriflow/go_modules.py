"""Bounded go.mod reading; a replaced module is not what a build resolves and is never matched."""

import re

from veriflow.domain import VeriFlowError

ECOSYSTEM = "go"
DECLARATION_NAMES = ("go.mod",)
# Vendored copies carry their own go.mod files and are not this module's declarations.
EXCLUDED_PARTS = ("vendor", "testdata")
BLOCK_DIRECTIVES = ("require", "replace", "exclude")
MODULE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~!/+-]{0,510}$")
VERSION = re.compile(r"^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def valid_version(value):
    return len(value) <= MAX_VERSION_CHARS and bool(VERSION.match(value))


LOCAL_PREFIXES = ("./", "../", "/", ".\\", "..\\")
MAX_REQUIREMENTS = 5_000
# Version text is untrusted manifest input.
MAX_VERSION_CHARS = 256


def valid_path(value):
    return bool(value) and bool(MODULE_PATH.match(value)) and ".." not in value.split("/")


def split_path(path):
    namespace, separator, name = path.rpartition("/")
    return (namespace, name) if separator else (None, path)


def purl(path, version):
    reference = f"pkg:golang/{path}"
    return f"{reference}@{version}" if version else reference


def record(path, version, resolution, scope, source, **extra):
    namespace, name = split_path(path)
    return {
        "ecosystem": ECOSYSTEM,
        "name": name,
        "namespace": namespace,
        "version": version,
        "purl": purl(path, version),
        "resolution": resolution,
        "scope": scope,
        "source_path": source,
        **extra,
    }


def statements(text):
    """Yield (directive, fields, comment) with block and single-line forms treated alike."""
    block = None
    for line in text.splitlines():
        body, _, comment = line.partition("//")
        fields = body.split()
        if not fields:
            continue
        if block is not None:
            if fields[0] == ")":
                block = None
                continue
            yield block, fields, comment.strip()
            continue
        if fields[0] in BLOCK_DIRECTIVES and len(fields) >= 2 and fields[1] == "(":
            block = fields[0]
            continue
        if fields[0] in BLOCK_DIRECTIVES and len(fields) >= 2:
            yield fields[0], fields[1:], comment.strip()


def parse_replacement(fields):
    """Return (replaced_path, replaced_version, target_path, target_version, local)."""
    if "=>" not in fields:
        return None
    marker = fields.index("=>")
    left, right = fields[:marker], fields[marker + 1 :]
    if not 1 <= len(left) <= 2 or not 1 <= len(right) <= 2 or not valid_path(left[0]):
        return None
    left_version = left[1] if len(left) == 2 and valid_version(left[1]) else None
    if len(left) == 2 and left_version is None:
        return None
    if right[0].startswith(LOCAL_PREFIXES):
        return left[0], left_version, None, None, True
    if not valid_path(right[0]):
        return None
    target_version = right[1] if len(right) == 2 and valid_version(right[1]) else None
    if len(right) != 2 or target_version is None:
        return None
    return left[0], left_version, right[0], target_version, False


def parse(raw, source):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [], "not_utf8", {}
    requirements, replacements, local, targets = [], {}, 0, []
    excluded = 0
    for directive, fields, comment in statements(text):
        if directive == "require" and len(fields) >= 2:
            path, version = fields[0], fields[1]
            if valid_path(path) and valid_version(version):
                indirect = comment.split()[:1] == ["indirect"]
                requirements.append((path, version, "indirect" if indirect else "direct"))
        elif directive == "exclude" and len(fields) >= 2:
            excluded += 1
        elif directive == "replace":
            parsed = parse_replacement(fields)
            if parsed is None:
                continue
            path, replaced_version, target, target_version, is_local = parsed
            replacements.setdefault(path, []).append(
                (replaced_version, is_local, target, target_version)
            )
    if len(requirements) > MAX_REQUIREMENTS:
        raise VeriFlowError(
            "go.mod exceeds the requirement limit; no partial inventory was produced"
        )
    records, replaced = [], 0
    for path, version, scope in requirements:
        # A replacement only applies when it names this version or no version at all.
        applied = [entry for entry in replacements.get(path, ()) if entry[0] in (None, version)]
        if not applied:
            records.append(
                record(path, version, "declared_version", scope, source, version_source="literal")
            )
            continue
        # A replaced requirement is not what a build resolves; never carry its version.
        replaced += 1
        records.append(record(path, None, "replaced", scope, source))
        for _, is_local, target, target_version in applied:
            if is_local:
                local += 1
            elif (target, target_version) not in targets:
                targets.append((target, target_version))
    for target, target_version in targets:
        records.append(
            record(
                target,
                target_version,
                "declared_version",
                "replacement",
                source,
                version_source="replacement_target",
            )
        )
    notes = {
        "indirect_requirements": sum(1 for _, _, scope in requirements if scope == "indirect"),
        "replaced_requirements": replaced,
        "local_replacements": local,
        "excluded_versions": excluded,
    }
    return records, None, {key: value for key, value in notes.items() if value}
