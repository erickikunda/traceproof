import json

import pytest
from test_dependency_discovery import properties_of
from test_dependency_discovery import snapshot as snapshot
from test_osv_matching import database as database
from test_osv_matching import osv

from traceproof.sbom_export import export_sbom

NS = 'xmlns="http://maven.apache.org/POM/4.0.0"'


def pom(body, namespace=True):
    return f"<project {NS if namespace else ''}>{body}</project>"


LITERAL = pom(
    """
    <groupId>com.example</groupId><artifactId>app</artifactId><version>1.0.0</version>
    <dependencies>
      <dependency>
        <groupId>org.springframework</groupId><artifactId>spring-web</artifactId>
        <version>5.3.9</version>
      </dependency>
      <dependency>
        <groupId>junit</groupId><artifactId>junit</artifactId>
        <version>4.13.2</version><scope>test</scope>
      </dependency>
    </dependencies>
    """
)


def libraries(store, repo, snapshot_id):
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    return {c["purl"]: c for c in document["components"] if c["type"] == "library"}


def coverage_of(store, repo, snapshot_id):
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True))
    return {p["name"]: p["value"] for p in document["metadata"]["properties"]}


def test_literal_versions_are_declared_not_pinned(store, snapshot):
    repo, snapshot_id = snapshot({"pom.xml": LITERAL})
    found = libraries(store, repo, snapshot_id)
    assert set(found) == {
        "pkg:maven/org.springframework/spring-web@5.3.9",
        "pkg:maven/junit/junit@4.13.2",
    }
    spring = found["pkg:maven/org.springframework/spring-web@5.3.9"]
    assert spring["group"] == "org.springframework" and spring["name"] == "spring-web"
    assert spring["version"] == "5.3.9"
    properties = properties_of(spring)
    # Maven has no lockfile; a literal version is a declaration, never a pin.
    assert properties["traceproof:resolution"] == "declared_version"
    assert properties["traceproof:version_source"] == "literal"
    junit = found["pkg:maven/junit/junit@4.13.2"]
    assert properties_of(junit)["traceproof:declared_scopes"] == "test"


def test_local_property_is_interpolated_and_marked(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
                <groupId>com.example</groupId><artifactId>app</artifactId><version>2.1.0</version>
                <properties><spring.version>5.3.9</spring.version></properties>
                <dependencies>
                  <dependency>
                    <groupId>org.springframework</groupId><artifactId>spring-web</artifactId>
                    <version>${spring.version}</version>
                  </dependency>
                  <dependency>
                    <groupId>com.example</groupId><artifactId>sibling</artifactId>
                    <version>${project.version}</version>
                  </dependency>
                </dependencies>
                """
            )
        }
    )
    found = libraries(store, repo, snapshot_id)
    spring = found["pkg:maven/org.springframework/spring-web@5.3.9"]
    # An interpolated version is not a literal one; say which the POM actually stated.
    assert properties_of(spring)["traceproof:version_source"] == "properties"
    assert properties_of(spring)["traceproof:resolution"] == "declared_version"
    assert "pkg:maven/com.example/sibling@2.1.0" in found


def test_unresolvable_property_never_invents_a_version(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
                <groupId>com.example</groupId><artifactId>app</artifactId>
                <dependencies>
                  <dependency>
                    <groupId>org.springframework</groupId><artifactId>spring-web</artifactId>
                    <version>${inherited.from.parent}</version>
                  </dependency>
                </dependencies>
                """
            )
        }
    )
    component = libraries(store, repo, snapshot_id)["pkg:maven/org.springframework/spring-web"]
    assert "version" not in component
    properties = properties_of(component)
    assert properties["traceproof:resolution"] == "unresolved_version"
    assert properties["traceproof:version_source"] == "inherited_or_managed_elsewhere"


def test_dependency_management_supplies_a_local_version(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
                <groupId>com.example</groupId><artifactId>app</artifactId>
                <dependencyManagement><dependencies>
                  <dependency>
                    <groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId>
                    <version>2.0.7</version>
                  </dependency>
                </dependencies></dependencyManagement>
                <dependencies>
                  <dependency>
                    <groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId>
                  </dependency>
                </dependencies>
                """
            )
        }
    )
    component = libraries(store, repo, snapshot_id)["pkg:maven/org.slf4j/slf4j-api@2.0.7"]
    assert properties_of(component)["traceproof:version_source"] == "dependency_management"


def test_imported_bom_is_counted_not_resolved(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
                <groupId>com.example</groupId><artifactId>app</artifactId>
                <dependencyManagement><dependencies>
                  <dependency>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-dependencies</artifactId>
                    <version>3.1.0</version><type>pom</type><scope>import</scope>
                  </dependency>
                </dependencies></dependencyManagement>
                <dependencies>
                  <dependency>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-starter-web</artifactId>
                  </dependency>
                </dependencies>
                """
            )
        }
    )
    found = libraries(store, repo, snapshot_id)
    starter = found["pkg:maven/org.springframework.boot/spring-boot-starter-web"]
    assert "version" not in starter
    notes = coverage_of(store, repo, snapshot_id)["traceproof:ecosystem_notes"]
    assert "maven_bom_imports_unresolved=1" in notes


def test_parent_and_profile_dependencies_are_recorded_as_gaps(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
                <parent>
                  <groupId>com.example</groupId><artifactId>root</artifactId>
                  <version>9.9.9</version>
                </parent>
                <artifactId>app</artifactId>
                <dependencies>
                  <dependency>
                    <groupId>com.example</groupId><artifactId>sibling</artifactId>
                    <version>${project.version}</version>
                  </dependency>
                </dependencies>
                <profiles><profile><id>native</id><dependencies>
                  <dependency>
                    <groupId>org.graalvm</groupId><artifactId>svm</artifactId><version>22.3</version>
                  </dependency>
                </dependencies></profile></profiles>
                """
            )
        }
    )
    notes = coverage_of(store, repo, snapshot_id)["traceproof:ecosystem_notes"]
    assert "maven_poms_with_parent=1" in notes
    assert "maven_profile_dependencies_ignored=1" in notes
    found = libraries(store, repo, snapshot_id)
    # A profile dependency is conditional; it is counted, never emitted as a component.
    assert not any("graalvm" in purl for purl in found)
    # The parent supplies project.version when the module omits its own.
    assert "pkg:maven/com.example/sibling@9.9.9" in found


def test_version_range_is_not_a_version(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
                <groupId>com.example</groupId><artifactId>app</artifactId>
                <dependencies>
                  <dependency>
                    <groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId>
                    <version>[1.7,2.0)</version>
                  </dependency>
                </dependencies>
                """
            )
        }
    )
    component = libraries(store, repo, snapshot_id)["pkg:maven/org.slf4j/slf4j-api"]
    assert "version" not in component
    properties = properties_of(component)
    assert properties["traceproof:resolution"] == "declared_range"
    assert properties["traceproof:version_constraint"] == "[1.7,2.0)"


def test_optional_dependency_is_marked_not_dropped(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
                <groupId>com.example</groupId><artifactId>app</artifactId>
                <dependencies>
                  <dependency>
                    <groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId>
                    <version>2.0.7</version><optional>true</optional><scope>provided</scope>
                  </dependency>
                </dependencies>
                """
            )
        }
    )
    component = libraries(store, repo, snapshot_id)["pkg:maven/org.slf4j/slf4j-api@2.0.7"]
    assert properties_of(component)["traceproof:declared_scopes"] == "optional,provided"


@pytest.mark.parametrize(
    "body",
    [
        '<!DOCTYPE project [<!ENTITY xxe "boom">]>',
        '<!DOCTYPE project SYSTEM "http://example.invalid/evil.dtd">',
        "<!ENTITY lol 'lol'>",
    ],
)
def test_entity_declarations_are_refused(store, snapshot, body):
    repo, snapshot_id = snapshot({"pom.xml": f'<?xml version="1.0"?>{body}{LITERAL}'})
    coverage = coverage_of(store, repo, snapshot_id)
    assert coverage["traceproof:dependency_files_skipped"] == "maven:doctype_refused=1"
    assert not libraries(store, repo, snapshot_id)


def test_entity_expansion_never_reaches_the_parser(store, snapshot):
    billion = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
        '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">]>'
        f"{LITERAL}"
    )
    repo, snapshot_id = snapshot({"pom.xml": billion})
    # Refused before parsing, not merely parsed to nothing.
    coverage = coverage_of(store, repo, snapshot_id)
    assert coverage["traceproof:dependency_files_skipped"] == "maven:doctype_refused=1"
    assert not libraries(store, repo, snapshot_id)


def test_malformed_and_foreign_xml_are_skipped(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": "<project><unclosed>",
            "module/pom.xml": '<settings xmlns="http://maven.apache.org/POM/4.0.0"/>',
        }
    )
    skipped = coverage_of(store, repo, snapshot_id)["traceproof:dependency_files_skipped"]
    assert "maven:not_xml=1" in skipped and "maven:unrecognized_shape=1" in skipped


def test_build_output_poms_are_ignored(store, snapshot):
    repo, snapshot_id = snapshot({"pom.xml": LITERAL, "target/classes/pom.xml": LITERAL})
    coverage = coverage_of(store, repo, snapshot_id)
    assert coverage["traceproof:excluded_declarations_ignored"] == "1"
    assert coverage["traceproof:dependency_files_parsed"] == "maven=1"


def test_namespaceless_pom_is_read(store, snapshot):
    repo, snapshot_id = snapshot(
        {
            "pom.xml": pom(
                """
        <groupId>com.example</groupId><artifactId>app</artifactId>
        <dependencies><dependency>
          <groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId><version>2.0.7</version>
        </dependency></dependencies>
        """,
                namespace=False,
            )
        }
    )
    assert "pkg:maven/org.slf4j/slf4j-api@2.0.7" in libraries(store, repo, snapshot_id)


def test_both_ecosystems_coexist(store, snapshot):
    repo, snapshot_id = snapshot(
        {"pom.xml": LITERAL, "package.json": {"dependencies": {"lodash": "^4.17.0"}}}
    )
    coverage = coverage_of(store, repo, snapshot_id)
    assert coverage["traceproof:dependency_ecosystems"] == "maven,npm"
    assert coverage["traceproof:dependency_files_parsed"] == "maven=1,npm=1"
    assert (
        coverage["traceproof:dependency_resolution_counts"] == "declared_range=1,declared_version=2"
    )
    found = libraries(store, repo, snapshot_id)
    assert "pkg:npm/lodash" in found and "pkg:maven/junit/junit@4.13.2" in found


def test_maven_export_is_deterministic(store, snapshot):
    repo, snapshot_id = snapshot({"pom.xml": LITERAL})
    assert export_sbom(store, repo, snapshot_id, packages=True) == export_sbom(
        store, repo, snapshot_id, packages=True
    )


def lexical_in_range(version, introduced, fixed):
    """What a naive string comparison would conclude, for contrast only."""
    return (introduced == "0" or version >= introduced) and version < fixed


@pytest.mark.parametrize(
    "version,introduced,fixed,affected,lexical_diverges",
    [
        # GHSA-9j36-3cp4-rh4j, org.xwiki.platform:xwiki-platform-administration-ui.
        # Lexically "13.10.1" < "4.2-milestone-1", so a string compare rejects it below
        # the lower bound and misses a real advisory.
        ("13.10.1", "4.2-milestone-1", "13.10.11", True, True),
        ("13.10.11", "4.2-milestone-1", "13.10.11", False, False),
        # GHSA-6m48-jxwx-76q7, org.apache.tomcat:tomcat. Lexically "6.0.3" > "6.0.21"
        # and < "6.0.37", so a string compare reports a version that is not affected.
        ("6.0.3", "6.0.21", "6.0.37", False, True),
        ("6.0.30", "6.0.21", "6.0.37", True, False),
    ],
)
def test_real_range_only_advisories_need_maven_ordering(
    store, snapshot, database, version, introduced, fixed, affected, lexical_diverges
):
    """Range bounds taken from live OSV records that carry no explicit version list."""
    assert (lexical_in_range(version, introduced, fixed) is not affected) is lexical_diverges
    body = (
        "<groupId>com.example</groupId><artifactId>app</artifactId><dependencies><dependency>"
        "<groupId>org.springframework</groupId><artifactId>spring-web</artifactId>"
        f"<version>{version}</version></dependency></dependencies>"
    )
    repo, snapshot_id = snapshot({"pom.xml": pom(body)})
    path = database(
        [
            osv(
                "GHSA-range-only",
                "Maven",
                "org.springframework:spring-web",
                ranges=[
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": introduced}, {"fixed": fixed}],
                    }
                ],
            )
        ]
    )
    document = json.loads(export_sbom(store, repo, snapshot_id, packages=True, database=path))
    found = document.get("vulnerabilities", [])
    assert bool(found) is affected
    properties = {p["name"]: p["value"] for p in document["metadata"]["properties"]}
    assert properties["traceproof:osv_evaluation_gaps"] == ""
    if affected:
        assert {p["value"] for p in found[0]["properties"]} >= {"maven_range"}
