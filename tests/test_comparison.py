import copy

import pytest
from test_reports import scanned as scanned
from test_triage import evidence_fixture as evidence_fixture
from typer.testing import CliRunner

from veriflow.cli import app
from veriflow.comparison import compare_reports, render_comparison
from veriflow.domain import VeriFlowError
from veriflow.reports import publish_report


@pytest.fixture
def pair(monkeypatch):
    candidate = {
        "fingerprint": "a",
        "rule_id": "py/code-injection",
        "tool_name": "CodeQL",
        "tool_version": "2.27.0",
        "path": "app.py",
        "line": 5,
        "end_line": 5,
        "sha256": "unchanged-file",
        "latest_advisory": "not_triaged",
    }
    before = {
        "repo_id": "repo",
        "snapshot_id": "snapshot-a",
        "created_at": "2026-01-01",
        "analysis_status": "completed",
        "execution_complete": True,
        "profile": "standard",
        "query_sha256": "query",
        "candidate_count": 1,
        "static_review_readiness": {"state": "ready_for_review"},
        "candidates": [candidate],
    }
    after = copy.deepcopy(before)
    after["created_at"] = "2026-01-02"
    monkeypatch.setattr(
        "veriflow.comparison.get_report",
        lambda store, repo, identity: before if identity == "before" else after,
    )
    return before, after


def compare():
    return compare_reports(None, "repo", "before", "after")


def test_exact_observation_and_advisory_change(pair):
    before, after = pair
    after["candidates"][0]["latest_advisory"] = "likely_false_positive"
    after["candidates"][0]["latest_simulated"] = True
    original = copy.deepcopy(pair)
    result = compare()
    assert result == compare() and pair == original
    row = result["rows"][0]
    assert row["status"] == "observed_in_both"
    assert row["baseline"][0]["occurrence_id"] == row["current"][0]["occurrence_id"]
    assert row["current"][0]["adjudication"] == "unreviewed"
    assert not row["resolution_verified"] and not result["coverage_comparable"]


def test_unchanged_file_anchor_is_only_possible_continuation(pair):
    _, after = pair
    after["snapshot_id"] = "snapshot-b"
    after["candidates"][0]["fingerprint"] = "b"
    result = compare()
    row = result["rows"][0]
    assert row["status"] == "possible_continuation"
    assert row["baseline"][0]["occurrence_id"] != row["current"][0]["occurrence_id"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "changed"),
        ("line", 6),
        ("path", "renamed.py"),
        ("tool_version", "other"),
        ("tool_version", "unknown"),
    ],
)
def test_changed_or_unknown_anchors_do_not_merge(pair, field, value):
    _, after = pair
    after["snapshot_id"] = "snapshot-b"
    after["candidates"][0].update(fingerprint="b", **{field: value})
    result = compare()
    assert {row["status"] for row in result["rows"]} == {"baseline_only", "current_only"}
    assert result["baseline_rows_accounted"] == result["current_rows_accounted"] == 1


def test_collision_keeps_every_observation(pair):
    before, after = pair
    after["snapshot_id"] = "snapshot-b"
    after["candidates"][0]["fingerprint"] = "b"
    before["candidates"].append({**before["candidates"][0], "fingerprint": "c"})
    before["candidate_count"] = 2
    result = compare()
    assert result["group_counts"]["ambiguous"] == 1
    assert len(result["rows"][0]["baseline"]) == 2
    assert result["baseline_rows_accounted"] == 2 and result["current_rows_accounted"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("query_sha256", None),
        ("query_sha256", "different"),
        ("profile", "other"),
        ("analysis_status", "failed"),
        ("execution_complete", False),
        ("created_at", "2025-01-01"),
    ],
)
def test_scope_mismatch_disables_anchor_matching(pair, field, value):
    _, after = pair
    after["snapshot_id"] = "snapshot-b"
    after["candidates"][0]["fingerprint"] = "b"
    after[field] = value
    result = compare()
    assert result["scope_gaps"] and not result["anchor_matching_enabled"]
    assert result["group_counts"]["possible_continuation"] == 0


def test_failed_empty_scan_never_resolves_missing_candidate(pair):
    _, after = pair
    after.update(
        analysis_status="failed", execution_complete=False, candidates=[], candidate_count=None
    )
    result = compare()
    assert result["current_candidate_count"] is None
    assert result["rows"][0]["status"] == "baseline_only"
    assert not result["rows"][0]["resolution_verified"]


@pytest.mark.parametrize("readiness", [None, {"state": "incomplete"}])
def test_missing_or_incomplete_readiness_disables_tentative_matching(pair, readiness):
    _, after = pair
    after["snapshot_id"] = "snapshot-b"
    after["candidates"][0]["fingerprint"] = "b"
    if readiness is None:
        after.pop("static_review_readiness")
    else:
        after["static_review_readiness"] = readiness
    result = compare()
    assert not result["anchor_matching_enabled"]
    assert "current:static_review_readiness_unknown_or_incomplete" in result["scope_gaps"]


def test_markdown_escapes_candidate_text(pair):
    before, after = pair
    for report in (before, after):
        report["candidates"][0]["path"] = "<script>```[x](https://bad)|"
    result = compare()
    text = render_comparison(result, "markdown")
    assert "<script>" not in text and "[x](https://bad)" not in text
    assert result["comparison_id"] in text
    with pytest.raises(VeriFlowError, match="format"):
        render_comparison(result, "unsupported")


def test_exact_published_reports_and_cli(store, scanned):
    repo = scanned[0]
    report = publish_report(store, repo)
    identity = report["report_id"]
    result = compare_reports(store, repo, identity, identity)
    assert result["group_counts"]["observed_in_both"] == 1
    with pytest.raises(VeriFlowError, match="belong"):
        compare_reports(store, "other-repo", identity, identity)
    output = CliRunner().invoke(
        app,
        [
            "--state-dir",
            str(store.root),
            "compare-reports",
            repo,
            identity,
            identity,
            "--format",
            "markdown",
        ],
    )
    assert output.exit_code == 0 and result["comparison_id"] in output.output
