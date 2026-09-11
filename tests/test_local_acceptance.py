import importlib.util
import json
import sys
from pathlib import Path

import pytest


def module():
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(
            "local_acceptance", scripts / "local_acceptance.py"
        )
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded
    finally:
        sys.path.remove(str(scripts))


def test_missing_report_is_failure(tmp_path):
    with pytest.raises(OSError):
        module().check_reports({"cases": [{"validation_path": str(tmp_path / "validation.json")}]})


def test_mismatched_report_is_failure(tmp_path):
    folder = tmp_path / "reports/gcs-scan"
    folder.mkdir(parents=True)
    (folder / "batch.json").write_text(
        json.dumps(dict(state="exported", items=[{"report_path": "report.json"}]))
    )
    (folder / "report.json").write_text(json.dumps(dict(report_id="wrong")))
    with pytest.raises(AssertionError):
        module().check_reports(
            {
                "cases": [
                    {"validation_path": str(tmp_path / "validation.json"), "report_id": "expected"}
                ]
            }
        )


def test_escaping_report_path_is_failure(tmp_path):
    folder = tmp_path / "reports/gcs-scan"
    folder.mkdir(parents=True)
    (folder / "batch.json").write_text(
        json.dumps(dict(state="exported", items=[{"report_path": "../../escape.json"}]))
    )
    with pytest.raises(AssertionError):
        module().check_reports({"cases": [{"validation_path": str(tmp_path / "validation.json")}]})
