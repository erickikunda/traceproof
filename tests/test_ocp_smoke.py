import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load(ROOT / "scripts/render_ocp_smoke.py")
smoke = load(ROOT / "containers/ocp_smoke.py")


def test_job_is_offline_and_disposable():
    result = renderer.bundle(
        "test", "smoke", "registry/image@sha256:" + "a" * 64, "input", "reports"
    )
    account, policy, job = result["items"]
    assert not account["automountServiceAccountToken"]
    assert policy["spec"]["egress"] == []
    assert policy["spec"]["policyTypes"] == ["Ingress", "Egress"]
    pod = job["spec"]["template"]["spec"]
    assert not pod["automountServiceAccountToken"]
    assert "runAsUser" not in pod["securityContext"]
    assert pod["securityContext"]["runAsNonRoot"]
    assert job["spec"]["backoffLimit"] == 0 and pod["restartPolicy"] == "Never"
    assert job["spec"]["activeDeadlineSeconds"] == 600
    container = pod["containers"][0]
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert not container["securityContext"]["allowPrivilegeEscalation"]
    assert container["securityContext"]["readOnlyRootFilesystem"]
    assert container["volumeMounts"][0]["readOnly"]
    assert all("emptyDir" in v for v in pod["volumes"][2:])
    assert "secret" not in json.dumps(result).lower()


@pytest.mark.parametrize(
    "change", [dict(namespace="../x"), dict(image="image:latest"), dict(reports_pvc="input")]
)
def test_bad_deployment_configuration(change):
    args = dict(
        namespace="test",
        name="smoke",
        image="registry/image@sha256:" + "a" * 64,
        input_pvc="input",
        reports_pvc="reports",
    )
    with pytest.raises(ValueError):
        renderer.bundle(**(args | change))


@pytest.mark.parametrize("content", ["", "source_type\ngit\n", "source_type\npvc\npvc\n"])
def test_invalid_input_exports_failure_without_scanning(tmp_path, monkeypatch, content):
    for name in ("input", "work", "reports"):
        (tmp_path / name).mkdir()
    (tmp_path / "input/input.csv").write_text(content)
    monkeypatch.setattr(smoke, "scan_run", lambda *a, **kw: pytest.fail("Unexpected scan"))
    with pytest.raises(ValueError):
        smoke.run(
            tmp_path / "input", tmp_path / "work", tmp_path / "reports", "test", Path("/tools")
        )
    report = json.loads((tmp_path / "reports/test/result.json").read_text())
    assert report["state"] == "failed" and report["model_calls"] == 0
    with pytest.raises(FileExistsError):
        smoke.run(
            tmp_path / "input", tmp_path / "work", tmp_path / "reports", "test", Path("/tools")
        )


@pytest.mark.parametrize("analysis_status", ["partial", "failed"])
@pytest.mark.parametrize("manifest_name", ["archives.csv", "input.csv"])
def test_published_failure_is_not_success(tmp_path, monkeypatch, analysis_status, manifest_name):
    for name in ("input", "work", "reports"):
        (tmp_path / name).mkdir()
    (tmp_path / "input" / manifest_name).write_text("repo_id,source_type\nexample,pvc\n")
    monkeypatch.setattr(smoke, "submit", lambda *a: "batch")
    monkeypatch.setattr(smoke, "process", lambda *a: {"items": [{"run_id": "run"}]})
    monkeypatch.setattr(
        smoke,
        "scan_run",
        lambda *a, **k: {
            "report_id": "report",
            "status": "incomplete",
            "analysis_status": analysis_status,
        },
    )
    report = {"report_id": "report", "static_review_readiness": {"state": "incomplete"}}
    monkeypatch.setattr(smoke, "get_report", lambda *a, **k: report)
    monkeypatch.setattr(smoke, "render_report", lambda *a: "{}")
    args = (tmp_path / "input", tmp_path / "work", tmp_path / "reports", "test", Path("/tools"))
    if analysis_status == "failed":
        with pytest.raises(ValueError):
            smoke.run(*args)
    else:
        assert smoke.run(*args)["state"] == "exported"
    result = json.loads((tmp_path / "reports/test/result.json").read_text())
    assert result["state"] == ("exported" if analysis_status == "partial" else "failed")
    assert (tmp_path / "reports/test/report.json").exists()

    assert result["manifest_name"] == manifest_name


@pytest.mark.parametrize(
    "language", ["java", "python", "javascript", "typescript", "go", "c", "cpp"]
)
def test_language_reaches_scan_and_export(tmp_path, monkeypatch, language):
    from veriflow.joern_claims import PROFILES

    known = {(p[0], p[1]) for p in PROFILES.values()}
    assert (language, smoke.PROFILES[language]) in known
    assert all(renderer.PROFILES[k] == v for k, v in smoke.PROFILES.items())
    rendered = renderer.bundle(
        "test", "smoke", "registry/image@sha256:" + "a" * 64, "input", "reports", language
    )
    container = rendered["items"][2]["spec"]["template"]["spec"]["containers"][0]
    assert container["args"] == ["--language", language]
    for name in ("input", "work", "reports"):
        (tmp_path / name).mkdir()
    (tmp_path / "input/input.csv").write_text("repo_id,source_type\nexample,pvc\n")
    monkeypatch.setattr(smoke, "submit", lambda *a: "batch")
    monkeypatch.setattr(smoke, "process", lambda *a: {"items": [{"run_id": "run"}]})

    def scan(*args, **kwargs):
        assert kwargs["language"] == language
        assert kwargs["joern_profile"] == (None if language == "java" else smoke.PROFILES[language])
        assert "advisory" not in kwargs
        return {"report_id": "report", "analysis_status": "partial"}

    monkeypatch.setattr(smoke, "scan_run", scan)
    monkeypatch.setattr(
        smoke,
        "get_report",
        lambda *a, **k: {"report_id": "report", "static_review_readiness": {"state": "incomplete"}},
    )
    monkeypatch.setattr(smoke, "render_report", lambda *a: "{}")
    result = smoke.run(
        tmp_path / "input",
        tmp_path / "work",
        tmp_path / "reports",
        "test",
        Path("/tools"),
        language,
    )
    assert result["language"] == language
    assert result["discovery_profile"] == smoke.PROFILES[language]


@pytest.mark.parametrize("language", ["csharp", "rust", "auto", "../python"])
def test_unavailable_toolchain_rejected_before_state(tmp_path, language):
    with pytest.raises(ValueError):
        smoke.run(tmp_path, tmp_path, tmp_path, "test", Path("/tools"), language)
    assert not list(tmp_path.iterdir())
    if language in {"csharp", "rust"}:
        return  # Renderer supports separate images; this runtime allowlist does not.
    with pytest.raises(ValueError):
        renderer.bundle(
            "test", "smoke", "registry/image@sha256:" + "a" * 64, "input", "reports", language
        )


@pytest.mark.parametrize(
    "language,tool,path",
    [
        ("csharp", "joern_repair_dir", "/opt/veriflow/csharp-repair"),
        ("rust", "rust_home", "/opt/rust"),
    ],
)
def test_specialized_image_preserves_tool_checks(tmp_path, monkeypatch, language, tool, path):
    profiles = json.loads((ROOT / f"containers/ocp-smoke-{language}-profiles.json").read_text())
    assert list(profiles) == [language]
    assert profiles[language] == renderer.PROFILES[language]
    monkeypatch.setattr(smoke, "PROFILES", profiles)
    rendered = renderer.bundle(
        "test", "smoke", "registry/image@sha256:" + "a" * 64, "input", "reports", language
    )
    assert rendered["items"][2]["spec"]["template"]["spec"]["containers"][0]["args"] == [
        "--language",
        language,
    ]
    for name in ("input", "work", "reports"):
        (tmp_path / name).mkdir()
    (tmp_path / "input/input.csv").write_text("repo_id,source_type\nexample,pvc\n")
    monkeypatch.setattr(smoke, "submit", lambda *a: "batch")
    monkeypatch.setattr(smoke, "process", lambda *a: {"items": [{"run_id": "run"}]})

    def reject_tool(*args, **kwargs):
        from veriflow.domain import TraceProofError

        assert kwargs[tool] == Path(path)
        assert kwargs["language"] == language
        assert kwargs["joern_profile"] == (None if language == "csharp" else profiles[language])
        assert "advisory" not in kwargs
        raise TraceProofError("Simulated invalid trusted tool identity")

    monkeypatch.setattr(smoke, "scan_run", reject_tool)
    from veriflow.domain import TraceProofError

    with pytest.raises(TraceProofError):
        smoke.run(
            tmp_path / "input",
            tmp_path / "work",
            tmp_path / "reports",
            "test",
            Path("/tools"),
            language,
        )
    result = json.loads((tmp_path / "reports/test/result.json").read_text())
    assert result["state"] == "failed" and result["model_calls"] == 0
    assert not (tmp_path / "reports/test/report.json").exists()
    with pytest.raises(ValueError):
        smoke.run(
            tmp_path / "input",
            tmp_path / "work",
            tmp_path / "reports",
            "other",
            Path("/tools"),
            "c",
        )
    assert not (tmp_path / "reports/other").exists()


@pytest.mark.parametrize("shape", ["missing", "both", "git", "mixed", "symlink", "directory"])
def test_manifest_selection_failures_never_scan(tmp_path, monkeypatch, shape):
    inputs, work, reports = [tmp_path / name for name in ("input", "work", "reports")]
    for path in (inputs, work, reports):
        path.mkdir()
    if shape in {"both", "mixed"}:
        (inputs / "archives.csv").write_text("source_type\npvc\n")
    if shape == "both":
        (inputs / "input.csv").write_text("source_type\npvc\n")
    if shape in {"git", "mixed"}:
        (inputs / "repositories.csv").write_text("url\nhttps://example.invalid/repo\n")
    if shape == "symlink":
        external = tmp_path / "external.csv"
        external.write_text("source_type\npvc\n")
        (inputs / "archives.csv").symlink_to(external)
    if shape == "directory":
        (inputs / "archives.csv").mkdir()
    monkeypatch.setattr(smoke, "scan_run", lambda *a, **k: pytest.fail("Unexpected scan"))
    from veriflow.domain import TraceProofError

    with pytest.raises((ValueError, OSError, TraceProofError)):
        smoke.run(inputs, work, reports, "test", Path("/tools"))
    assert not list(work.iterdir())
    assert json.loads((reports / "test/result.json").read_text())["state"] == "failed"
