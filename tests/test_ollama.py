import io
import json
import subprocess

import pytest
from pydantic import ValidationError
from test_triage import evidence_fixture as evidence_fixture

from traceproof import models
from traceproof.bundles import build_bundle
from traceproof.triage import set_budget, triage


def policy(**changes):
    return models.ModelConfig.model_validate(
        {
            "provider": "ollama",
            "model": "local-model",
            "endpoint": "http://127.0.0.1:11434/api/chat",
            "allowed_endpoint_hosts": ["127.0.0.1"],
            "allow_source_transmission": True,
            **changes,
        }
    )


def response(**changes):
    return json.dumps(
        {
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "eval_count": 20,
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "verdict": "abstain",
                        "rationale": "Insufficient evidence",
                        "evidence_ids": [],
                        "counterevidence": "",
                        "claims": [],
                    }
                ),
            },
            **changes,
        }
    ).encode()


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com:11434/api/chat",
        "http://localhost:11434/api/chat",
        "http://127.0.0.1:11434/api/chat?redirect=x",
        "https://127.0.0.1:11434/api/chat",
        "http://127.0.0.1:11434/api/generate",
    ],
)
def test_loopback_policy(endpoint):
    with pytest.raises(ValidationError):
        policy(endpoint=endpoint)
    with pytest.raises(ValidationError):
        policy(model="model-cloud")


def test_wire_and_response_contract():
    body = models.request_body({"rule_id": "py/code-injection"}, policy())
    assert body["stream"] is False and body["think"] is False
    assert body["options"]["num_predict"] == 1024
    assert body["format"]["additionalProperties"] is False
    assert "$defs" not in body["format"]
    assert "maxLength" not in body["format"]["properties"]["rationale"]
    assert models.parse_ollama_response(response()).usage.input_tokens == 10
    assert models.parse_ollama_response(response(done_reason="length")).status == "incomplete"
    assert (
        models.parse_ollama_response(
            response(message={"role": "assistant", "content": "no"})
        ).status
        == "invalid_output"
    )
    doc = json.loads(response())
    decision = json.loads(doc["message"]["content"])
    decision["rationale"] = "x" * 2001
    doc["message"]["content"] = json.dumps(decision)
    assert models.parse_ollama_response(json.dumps(doc)).status == "invalid_output"
    with pytest.raises(ValidationError):
        models.parse_ollama_response(response(eval_count=True))
    with pytest.raises(models.TraceProofError, match="context budget"):
        models.request_body({"rule_id": "py/code-injection", "source": "x" * 40000}, policy())


def test_transport_uses_no_credentials(monkeypatch):
    captured = {}
    monkeypatch.setenv("TRACEPROOF_OPENAI_API_KEY", "do-not-forward")

    def run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            command, 0, models.Reply(status="incomplete").model_dump_json().encode()
        )

    monkeypatch.setattr(models.subprocess, "run", run)
    adapter = models.live_adapter(policy())
    adapter.invoke({})
    assert captured["env"] == {} and captured["timeout"] == 63

    class Opener:
        def open(self, request, timeout):
            assert request.get_header("Authorization") is None
            assert request.get_header("X-api-key") is None
            return io.BytesIO(response())

    monkeypatch.setattr(models.urllib.request, "build_opener", lambda *a: Opener())
    assert adapter._invoke_https({}).status == "completed"


def test_real_provider_ledger_optin_and_reuse(store, evidence_fixture):
    run, attempt, fingerprint, _ = evidence_fixture()
    bundle = build_bundle(store, attempt, fingerprint)
    set_budget(store, run, 100000)

    class Adapter:
        identity = "ollama-test"
        calls = 0

        def invoke(self, body):
            self.calls += 1
            return models.parse_ollama_response(response())

    adapter = Adapter()
    with pytest.raises(models.TraceProofError, match="disabled"):
        triage(
            store, bundle["bundle_id"], policy(allow_source_transmission=False), adapter, "disabled"
        )
    with pytest.raises(models.TraceProofError, match="classification"):
        triage(store, bundle["bundle_id"], policy(allowed_classifications=[]), adapter, "denied")
    first = triage(store, bundle["bundle_id"], policy(), adapter, "local-1")
    triage(store, bundle["bundle_id"], policy(), adapter, "local-1")
    assert adapter.calls == 1
    assert first["provider"] == "ollama" and first["simulated"] is False
