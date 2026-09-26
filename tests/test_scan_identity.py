import copy

import pytest

from veriflow.scan_identity import analysis_identity


def configuration():
    return {
        "scanner": {"engine_id": "codeql", "version": "1", "adapter_version": "1"},
        "snapshot_id": "source-a",
        "language": "java",
        "language_scope": {"profile": "spring"},
        "prepared_input": {"tool_version": "1", "kind": "codeql_database"},
        "rule_entry": {"sha256": "entry-a", "transitive_dependencies_verified": False},
        "requested_resources": {"threads": 2, "ram_mb": 2048},
        "timeout_seconds": 600,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("scanner", {"engine_id": "joern", "version": "1", "adapter_version": "1"}),
        ("scanner", {"engine_id": "codeql", "version": "2", "adapter_version": "1"}),
        ("scanner", {"engine_id": "codeql", "version": "1", "adapter_version": "2"}),
        ("rule_entry", {"sha256": "entry-b", "transitive_dependencies_verified": False}),
        ("snapshot_id", "source-b"),
        ("language_scope", {"profile": "different"}),
        ("prepared_input", {"tool_version": "2", "kind": "codeql_database"}),
    ],
)
def test_configuration_changes_invalidate_recorded_identity(field, value):
    original = configuration()
    changed = copy.deepcopy(original)
    changed[field] = value
    assert analysis_identity(original) != analysis_identity(changed)
    assert analysis_identity(changed)["automatic_reuse_eligible"] is False


def test_attempt_ids_and_dictionary_order_do_not_change_configuration_identity():
    original = configuration()
    reordered = dict(reversed(list(original.items())))
    reordered["attempt_id"] = "new-attempt"
    assert analysis_identity(original) == analysis_identity(reordered)
    assert analysis_identity(original)["automatic_reuse_eligible"] is False
