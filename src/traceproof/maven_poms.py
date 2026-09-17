"""Bounded pom.xml reading with entity declarations refused; POM inheritance is never resolved."""

import re
import xml.etree.ElementTree as ElementTree

from traceproof.domain import TraceProofError

ECOSYSTEM = "maven"
DECLARATION_NAMES = ("pom.xml",)
# Build output holds copied descriptors, not declarations.
EXCLUDED_PARTS = ("target",)
# A pom.xml needs no DTD; refuse one rather than expand entities under an attacker's control.
FORBIDDEN = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
PROPERTY = re.compile(r"\$\{([^{}$]+)\}")
RANGE_PREFIX = ("[", "(")
MAX_DEPENDENCIES = 5_000
# Version text is untrusted manifest input.
MAX_VERSION_CHARS = 256


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child_text(element, name):
    for child in element:
        if local(child.tag) == name:
            return (child.text or "").strip()
    return None


def child_element(element, name):
    for child in element:
        if local(child.tag) == name:
            return child
    return None


def project_properties(root):
    """Collect this file's own properties; inherited and profile properties stay unresolved."""
    values = {}
    declared = child_element(root, "properties")
    for child in declared if declared is not None else ():
        text = (child.text or "").strip()
        if "${" not in text:
            values[local(child.tag)] = text
    parent = child_element(root, "parent")
    for key, name in (("project.version", "version"), ("project.groupId", "groupId")):
        value = child_text(root, name) or (child_text(parent, name) if parent is not None else None)
        if value and "${" not in value:
            values[key] = values[f"pom.{name.split('.')[-1]}"] = value
    return values


def interpolate(value, properties):
    """Substitute this file's properties once; a surviving placeholder stays unresolved."""
    if not value or "${" not in value:
        return value

    def substitute(match):
        return properties.get(match.group(1).strip(), match.group(0))

    resolved = PROPERTY.sub(substitute, value)
    return None if "${" in resolved else resolved


def coordinate(element, properties):
    group = interpolate(child_text(element, "groupId"), properties)
    artifact = interpolate(child_text(element, "artifactId"), properties)
    if not group or not artifact or any(c in group + artifact for c in "/?#@ "):
        return None, None
    return group, artifact


def purl(group, artifact, version):
    reference = f"pkg:maven/{group}/{artifact}"
    return f"{reference}@{version}" if version else reference


def managed_versions(root, properties):
    """Versions this file manages for its own dependencies; imported BOMs are not resolved."""
    managed, imports = {}, 0
    section = child_element(root, "dependencyManagement")
    listed = child_element(section, "dependencies") if section is not None else None
    for element in listed if listed is not None else ():
        if local(element.tag) != "dependency":
            continue
        group, artifact = coordinate(element, properties)
        if group is None:
            continue
        if child_text(element, "scope") == "import":
            imports += 1
            continue
        version = interpolate(child_text(element, "version"), properties)
        if version:
            managed[(group, artifact)] = version
    return managed, imports


def classify(version, managed_version, interpolated):
    """Decide what a POM actually establishes about a version; Maven has no lockfile."""
    origin = "properties" if interpolated else "literal"
    if not version:
        if not managed_version:
            return None, "unresolved_version", "inherited_or_managed_elsewhere", None
        version, origin = managed_version, "dependency_management"
    if len(version) > MAX_VERSION_CHARS:
        return None, "unresolved_version", "version_not_bounded", None
    # A managed version can itself be a range, and a range is never a component version.
    if version.startswith(RANGE_PREFIX):
        return None, "declared_range", origin, version
    return version, "declared_version", origin, None


def scopes_of(element):
    scope = child_text(element, "scope") or "compile"
    return f"{scope},optional" if child_text(element, "optional") == "true" else scope


def parse(raw, source):
    if FORBIDDEN.search(raw):
        return [], "doctype_refused", {}
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        return [], "not_xml", {}
    if local(root.tag) != "project":
        return [], "unrecognized_shape", {}
    properties = project_properties(root)
    managed, imports = managed_versions(root, properties)
    notes = {
        "poms_with_parent": 1 if child_element(root, "parent") is not None else 0,
        "bom_imports_unresolved": imports,
        "profile_dependencies_ignored": 0,
    }
    profiles = child_element(root, "profiles")
    for profile in profiles if profiles is not None else ():
        section = child_element(profile, "dependencies")
        notes["profile_dependencies_ignored"] += len(section) if section is not None else 0
    records = []
    listed = child_element(root, "dependencies")
    declared = [e for e in (listed if listed is not None else ()) if local(e.tag) == "dependency"]
    if len(declared) > MAX_DEPENDENCIES:
        raise TraceProofError("POM exceeds the dependency limit; no partial inventory was produced")
    for element in declared:
        group, artifact = coordinate(element, properties)
        if group is None:
            continue
        stated = child_text(element, "version")
        declared = interpolate(stated, properties)
        version, resolution, source_kind, constraint = classify(
            declared, managed.get((group, artifact)), bool(stated) and "${" in stated
        )
        records.append(
            {
                "ecosystem": ECOSYSTEM,
                "name": artifact,
                "namespace": group,
                "version": version,
                "purl": purl(group, artifact, version),
                "resolution": resolution,
                "scope": scopes_of(element),
                "source_path": source,
                "version_source": source_kind,
                "constraint": constraint,
            }
        )
    return records, None, notes
