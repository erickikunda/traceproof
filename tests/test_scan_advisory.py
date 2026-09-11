from pathlib import Path

import pytest
from test_joern_advisory import adapter_for
from test_joern_claims import audited_bundle as audited_bundle
from test_slice03 import captured_source as captured_source
from test_triage import policy

from traceproof import pipeline
from traceproof.domain import TraceProofError
from traceproof.joern_claims import POLICY
from traceproof.reports import get_report
from traceproof.scan_advisory import AdvisoryOptions, load_advisory
from traceproof.triage import set_budget


def options(bundle, **kwargs):
    return AdvisoryOptions(policy(), adapter_for(bundle), "pipeline-advice", POLICY, **kwargs)


def test_scan_to_advisory_to_exact_report(store, audited_bundle, tmp_path):
    b = audited_bundle
    set_budget(store, b["run_id"], 100000)
    advisory = options(b)
    result = pipeline.scan_run(
        store,
        b["run_id"],
        engine="joern",
        language="auto",
        joern_home=tmp_path / "tools",
        advisory=advisory,
    )
    assert result["status"] == "incomplete" and result["model_calls"] == 1
    assert result["live_model_calls"] == 0 and result["advisory"]["status"] == "page_complete"
    report = get_report(store, b["repo_id"], report_id=result["report_id"])
    assert report["attempt_id"] == result["attempt_id"] != b["attempt_id"]
    assert report["candidates"][0]["latest_advisory"] == "needs_review"
    assert report["candidates"][0]["triage_history"][0]["simulated"]
    skipped = pipeline.scan_run(
        store,
        b["run_id"],
        engine="joern",
        language="auto",
        joern_home=tmp_path / "tools",
        advisory=advisory,
        skip_existing=True,
    )
    assert skipped["status"] == "skipped_existing_attempt" and skipped["model_calls"] == 0
    assert skipped["advisory"]["status"] == "skipped_existing_attempt"
    assert advisory.adapter.calls == 1


@pytest.mark.parametrize("case", ["budget", "requests", "page", "scan_failure"])
def test_stops_and_empty_page_still_publish(store, audited_bundle, tmp_path, monkeypatch, case):
    b = audited_bundle
    set_budget(
        store,
        b["run_id"],
        0 if case == "budget" else 100000,
        max_requests=0 if case == "requests" else 5,
    )
    advisory = options(b, offset=1 if case == "page" else 0)
    if case == "scan_failure":

        def fail(*args, **kwargs):
            raise TraceProofError("synthetic scanner failure")

        monkeypatch.setattr("traceproof.joern.stage", fail)
    result = pipeline.scan_run(
        store,
        b["run_id"],
        engine="joern",
        language="java",
        joern_home=tmp_path / "tools",
        advisory=advisory,
    )
    assert result["report_id"] and result["model_calls"] == 0
    assert advisory.adapter.calls == 0
    assert result["advisory"]["status"] == (
        "skipped_analysis_failed"
        if case == "scan_failure"
        else "page_complete"
        if case == "page"
        else "halted"
    )


def test_missing_budget_and_wrong_engine_rejected(store, audited_bundle, tmp_path):
    b = audited_bundle
    with pytest.raises(TraceProofError, match="budget"):
        pipeline.scan_run(
            store,
            b["run_id"],
            engine="joern",
            language="java",
            joern_home=tmp_path / "tools",
            advisory=options(b),
        )
    with pytest.raises(TraceProofError, match="engine joern"):
        pipeline.scan_run(store, b["run_id"], advisory=options(b))
    with pytest.raises(TraceProofError, match="java profile"):
        pipeline.scan_run(
            store,
            b["run_id"],
            engine="joern",
            language="python",
            joern_home=tmp_path / "tools",
            advisory=options(b),
        )


@pytest.mark.parametrize("kwargs", [{"offset": -1}, {"limit": 0}, {"limit": 101}])
def test_page_bounds(audited_bundle, kwargs):
    with pytest.raises(TraceProofError, match="page"):
        options(audited_bundle, **kwargs)


def test_cli_options_require_complete_opt_in():
    assert load_advisory(None, None, None, None) is None
    with pytest.raises(TraceProofError, match="advisory-config"):
        load_advisory(None, POLICY, "key", None)
    with pytest.raises(TraceProofError, match="review-policy"):
        load_advisory(Path("unused"), None, "key", None)


def test_cli_scan_advisory_full_path(store, audited_bundle, tmp_path):
    import json

    from typer.testing import CliRunner

    from traceproof.cli import app

    b = audited_bundle
    set_budget(store, b["run_id"], 100000)
    config, replay = tmp_path / "policy.json", tmp_path / "reply.json"
    config.write_text(policy().model_dump_json())
    replay.write_text(adapter_for(b).reply.model_dump_json())
    result = CliRunner().invoke(
        app,
        [
            "--state-dir",
            str(store.root),
            "scan-run",
            b["run_id"],
            "--engine",
            "joern",
            "--language",
            "auto",
            "--joern-home",
            str(tmp_path / "tools"),
            "--advisory-config",
            str(config),
            "--review-policy",
            POLICY,
            "--advisory-key",
            "cli-workflow",
            "--replay",
            str(replay),
        ],
    )
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert document["model_calls"] == 1 and document["live_model_calls"] == 0
    assert document["advisory"]["items"][0]["disposition"] == "needs_review"
