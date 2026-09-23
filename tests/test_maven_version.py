import pytest

from veriflow.maven_version import MavenVersion, comparable_qualifier, maven_key

# Ordering vectors from Maven's own ComparableVersionTest.
QUALIFIER_ORDER = [
    "1-alpha2snapshot",
    "1-alpha2",
    "1-alpha-123",
    "1-beta-2",
    "1-beta123",
    "1-m2",
    "1-m11",
    "1-rc",
    "1-cr2",
    "1-rc123",
    "1-SNAPSHOT",
    "1",
    "1-sp",
    "1-sp2",
    "1-sp123",
    "1-abc",
    "1-def",
    "1-pl",
    "1-2",
    "1.0.1",
]
NUMBER_ORDER = [
    "2.0",
    "2-1",
    "2.0.a",
    "2.0.0.a",
    "2.0.2",
    "2.0.123",
    "2.1.0",
    "2.1-a",
    "2.1b",
    "2.1-c",
    "2.1-1",
    "2.1.0.1",
    "2.2",
    "2.123",
    "11.a2",
    "11.a11",
    "11.b2",
    "11.b11",
    "11.m2",
    "11.m11",
    "11",
    "11.a",
    "11b",
    "11c",
    "11m",
]
EQUIVALENT = [
    ("1", "1.0"),
    ("1", "1.0.0"),
    ("1.0", "1.0.0"),
    ("1", "1-0"),
    ("1", "1.0-0"),
    ("1.0", "1.0-0"),
    ("1a", "1-a"),
    ("1a", "1.0-a"),
    ("1a", "1.0.0-a"),
    ("1.0a", "1-a"),
    ("1.0.0a", "1-a"),
    ("1x", "1-x"),
    ("1.0x", "1-x"),
    ("1.0.0x", "1-x"),
    ("1ga", "1"),
    ("1release", "1"),
    ("1final", "1"),
    ("1cr", "1rc"),
    ("1SNAPSHOT", "1-snapshot"),
    ("1sp", "1-sp"),
    ("1ga", "1.0.0"),
    ("1final", "1.0.0"),
]


@pytest.mark.parametrize("sequence", [QUALIFIER_ORDER, NUMBER_ORDER])
def test_maven_reference_orderings(sequence):
    parsed = [MavenVersion(value) for value in sequence]
    assert all(parsed[i] < parsed[i + 1] for i in range(len(parsed) - 1))
    assert [version.text for version in sorted(parsed)] == sequence


@pytest.mark.parametrize("left,right", EQUIVALENT)
def test_padding_and_aliases_are_equivalent(left, right):
    assert MavenVersion(left) == MavenVersion(right)
    assert not MavenVersion(left) < MavenVersion(right)
    assert MavenVersion(left) >= MavenVersion(right)


def test_release_qualifiers_do_not_outrank_the_release():
    assert MavenVersion("3.1.0") == MavenVersion("3.1.0.RELEASE")
    assert MavenVersion("5.3.9.RELEASE") < MavenVersion("5.3.10.RELEASE")


def test_numeric_segments_are_not_compared_as_text():
    assert MavenVersion("2.0.7") < MavenVersion("2.0.10")
    assert MavenVersion("1.9") < MavenVersion("1.10")
    assert MavenVersion("1.0.0009") == MavenVersion("1.0.9")


def test_prerelease_qualifiers_sort_below_the_release():
    for qualifier in ("alpha", "beta", "milestone", "rc", "snapshot"):
        assert MavenVersion(f"1.0-{qualifier}") < MavenVersion("1.0")
    assert MavenVersion("1.0") < MavenVersion("1.0-sp")


def test_unknown_qualifiers_sort_after_known_ones_by_name():
    assert comparable_qualifier("alpha") == "0"
    assert comparable_qualifier("zeta").startswith("7-")
    assert MavenVersion("1.0-rc") < MavenVersion("1.0-zeta")


def test_case_is_normalized():
    assert MavenVersion("1.0-SNAPSHOT") == MavenVersion("1.0-snapshot")
    assert MavenVersion("1.0-Final") == MavenVersion("1.0")


def test_key_rejects_blank_input_and_orders_are_total():
    assert maven_key("") is None and maven_key(None) is None
    assert maven_key("  1.0  ").text == "1.0"
    # Every string orders against every other; nothing is left unevaluated.
    values = [MavenVersion(v) for v in ("1.0", "junk", "", "1.0-x", "0")]
    assert len(sorted(values)) == len(values)
