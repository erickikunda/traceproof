"""Maven ComparableVersion ordering; qualifier aliasing and padding follow the Maven algorithm."""

QUALIFIERS = ("alpha", "beta", "milestone", "rc", "snapshot", "", "sp")
ALIASES = {"ga": "", "final": "", "release": "", "cr": "rc"}
SHORTHAND = {"a": "alpha", "b": "beta", "m": "milestone"}
RELEASE_INDEX = str(QUALIFIERS.index(""))
# Version text is untrusted manifest input; refuse it before converting a segment.
MAX_VERSION_CHARS = 256


def comparable_qualifier(value):
    """Unknown qualifiers sort after every known one, by name."""
    return str(QUALIFIERS.index(value)) if value in QUALIFIERS else f"{len(QUALIFIERS)}-{value}"


def sign(value):
    return (value > 0) - (value < 0)


def string_item(value, followed_by_digit):
    if followed_by_digit and len(value) == 1:
        value = SHORTHAND.get(value, value)
    return ("str", ALIASES.get(value, value))


def parse_item(is_digit, buffer):
    if is_digit:
        stripped = buffer.lstrip("0")
        return ("int", int(stripped) if stripped else 0)
    return string_item(buffer, False)


def is_null(item):
    kind, value = item
    if kind == "int":
        return value == 0
    if kind == "str":
        return comparable_qualifier(value) == RELEASE_INDEX
    return not value


def normalize(items):
    """Drop trailing padding so 1, 1.0 and 1.0.0-ga order identically."""
    for index in range(len(items) - 1, -1, -1):
        if is_null(items[index]):
            del items[index]
        elif items[index][0] != "list":
            break


def parse(version):
    if not isinstance(version, str) or len(version) > MAX_VERSION_CHARS:
        raise ValueError("Maven version exceeds the accepted length")
    root = []
    stack, current, items = [root], root, [root]
    is_digit, start = False, 0
    value = version.lower()
    for index, character in enumerate(value):
        if character in ".-":
            current.append(
                ("int", 0) if index == start else parse_item(is_digit, value[start:index])
            )
            start = index + 1
            if character == "-":
                nested = []
                current.append(("list", nested))
                stack.append(nested)
                items.append(nested)
                current = nested
        elif character.isdigit():
            if not is_digit and index > start:
                current.append(string_item(value[start:index], True))
                start = index
                nested = []
                current.append(("list", nested))
                stack.append(nested)
                items.append(nested)
                current = nested
            is_digit = True
        else:
            if is_digit and index > start:
                current.append(parse_item(True, value[start:index]))
                start = index
                nested = []
                current.append(("list", nested))
                stack.append(nested)
                items.append(nested)
                current = nested
            is_digit = False
    if len(value) > start:
        current.append(parse_item(is_digit, value[start:]))
    while stack:
        normalize(stack.pop())
    return ("list", root)


def compare_to_null(item):
    kind, value = item
    if kind == "int":
        return 0 if value == 0 else 1
    if kind == "str":
        return sign(
            (comparable_qualifier(value) > RELEASE_INDEX)
            - (comparable_qualifier(value) < RELEASE_INDEX)
        )
    return compare_to_null(value[0]) if value else 0


def compare_lists(left, right):
    for index in range(max(len(left), len(right))):
        first = left[index] if index < len(left) else None
        second = right[index] if index < len(right) else None
        if first is None:
            result = 0 if second is None else -compare_to_null(second)
        elif second is None:
            result = compare_to_null(first)
        else:
            result = compare(first, second)
        if result != 0:
            return result
    return 0


def compare(left, right):
    """Integers outrank qualifiers, which outrank nested lists, exactly as Maven orders them."""
    kind, value = left
    other_kind, other_value = right
    if kind == "int":
        return sign(value - other_value) if other_kind == "int" else 1
    if kind == "str":
        if other_kind == "int":
            return -1
        if other_kind == "list":
            return -1
        first, second = comparable_qualifier(value), comparable_qualifier(other_value)
        return sign((first > second) - (first < second))
    if other_kind == "int":
        return -1
    if other_kind == "str":
        return 1
    return compare_lists(value, other_value)


class MavenVersion:
    """Orders Maven versions; comparison is total, so no range is left unevaluated."""

    __slots__ = ("parsed", "text")

    def __init__(self, text):
        self.text = text
        self.parsed = parse(text)

    def __eq__(self, other):
        return isinstance(other, MavenVersion) and compare(self.parsed, other.parsed) == 0

    def __lt__(self, other):
        return compare(self.parsed, other.parsed) < 0

    def __le__(self, other):
        return compare(self.parsed, other.parsed) <= 0

    def __gt__(self, other):
        return compare(self.parsed, other.parsed) > 0

    def __ge__(self, other):
        return compare(self.parsed, other.parsed) >= 0

    def __hash__(self):
        return hash(self.text)


def maven_key(value):
    """Return None rather than raise, so an unorderable version becomes a recorded gap."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return MavenVersion(value.strip())
    except ValueError:
        return None
