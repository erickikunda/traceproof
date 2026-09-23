from types import SimpleNamespace

from veriflow.joern_diagnostics import LIMIT, observe_logs


def test_parser_events_deduplicate_files_without_exposing_messages(tmp_path):
    line = (
        "2026-09-10 18:09:30.950 \x1b[33mWARN \x1b[m SourceParser Failed to process 'Broken.java'"
    )
    (tmp_path / "prepare.log").write_text(line + "\n" + line + "\n")
    report = observe_logs(tmp_path, [SimpleNamespace(path="Broken.java")])
    stage = report["stages"]["prepare"]
    assert stage["warning_events"] == 2
    assert stage["parser_problem_files"] == ["Broken.java"]
    assert report["stages"]["analyze"]["state"] == "unavailable"
    assert report["authoritative"] is False
    assert "Failed to process" not in str(report)


def test_absent_events_do_not_claim_success_and_truncation_is_visible(tmp_path):
    (tmp_path / "prepare.log").write_bytes(b"x" * (LIMIT + 10))
    (tmp_path / "analyze.log").write_bytes(b"")
    report = observe_logs(tmp_path, [])
    assert report["stages"]["prepare"]["state"] == "truncated"
    assert report["stages"]["prepare"]["inspected_bytes"] == LIMIT
    assert report["stages"]["analyze"]["warning_events"] == 0
    assert report["parse_completeness_verified"] is False


def test_unknown_paths_are_not_bound_by_basename(tmp_path):
    (tmp_path / "prepare.log").write_text(
        "2026-09-10 18:09:30.950 WARN SourceParser Failed to process 'Broken.java'\n"
    )
    report = observe_logs(tmp_path, [SimpleNamespace(path="nested/Broken.java")])
    stage = report["stages"]["prepare"]
    assert stage["parser_problem_files"] == []
    assert stage["unmapped_parser_events"] == 1
