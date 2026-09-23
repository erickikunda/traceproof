"""Offline Messages contract: no credentials or external calls."""

import io
import json

import pytest
from pydantic import ValidationError

from veriflow import models


def policy(**changes):
    return models.ModelConfig.model_validate(
        {
            "provider": "anthropic",
            "model": "operator-selected",
            "endpoint": "https://approved.example/v1/messages",
            "allowed_endpoint_hosts": ["approved.example"],
            "api_key_env": "TRACEPROOF_ANTHROPIC_API_KEY",
            "allow_source_transmission": True,
            "input_micro_usd_per_1k": 1000,
            **changes,
        }
    )


def response(**changes):
    return json.dumps(
        {
            "type": "message",
            "role": "assistant",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "verdict": "abstain",
                            "rationale": "Insufficient evidence",
                            "evidence_ids": [],
                            "counterevidence": "",
                            "claims": [],
                        }
                    ),
                }
            ],
            **changes,
        }
    ).encode()


def test_wire_schema_and_local_constraints():
    body = models.request_body({"rule_id": "py/code-injection"}, policy())
    assert body["messages"][0]["role"] == "user"
    assert body["max_tokens"] == 1024
    schema = body["output_config"]["format"]["schema"]
    assert "maxLength" not in schema["properties"]["rationale"]
    assert "2000" in schema["properties"]["rationale"]["description"]
    assert not {"tools", "cache_control", "store"} & body.keys()
    doc = json.loads(response())
    decision = json.loads(doc["content"][0]["text"])
    decision["rationale"] = "x" * 2001
    doc["content"][0]["text"] = json.dumps(decision)
    assert models.parse_anthropic_response(json.dumps(doc)).status == "invalid_output"


@pytest.mark.parametrize(
    "reason,status",
    [
        ("end_turn", "completed"),
        ("refusal", "refused"),
        ("max_tokens", "incomplete"),
        ("tool_use", "incomplete"),
    ],
)
def test_stop_reasons(reason, status):
    reply = models.parse_anthropic_response(response(stop_reason=reason))
    assert reply.status == status
    assert reply.usage.input_tokens == 10


def test_unexpected_content_and_cache_usage():
    assert (
        models.parse_anthropic_response(response(content=[{"type": "tool_use"}])).status
        == "invalid_output"
    )
    assert (
        models.parse_anthropic_response(
            response(
                usage={"input_tokens": 10, "output_tokens": 20, "cache_creation_input_tokens": 30}
            )
        ).usage
        is None
    )
    with pytest.raises(ValidationError):
        models.parse_anthropic_response(response(usage={"input_tokens": True, "output_tokens": 20}))


def test_transport_headers_and_policy(monkeypatch):
    config = policy()
    captured = {}

    class Opener:
        def open(self, request, timeout):
            captured.update(
                headers=dict(request.header_items()), body=request.data, timeout=timeout
            )
            return io.BytesIO(response())

    monkeypatch.setenv(config.api_key_env, "synthetic-key")
    monkeypatch.setattr(models.urllib.request, "build_opener", lambda *args: Opener())
    adapter = models.live_adapter(config)
    assert isinstance(adapter, models.AnthropicAdapter)
    assert (
        adapter._invoke_https(models.request_body({"rule_id": "py/code-injection"}, config)).status
        == "completed"
    )
    assert captured["headers"]["X-api-key"] == "synthetic-key"
    assert captured["headers"]["Anthropic-version"] == "2023-06-01"
    assert b"synthetic-key" not in captured["body"]
    assert captured["timeout"] == 60
    with pytest.raises(models.TraceProofError, match="disabled"):
        models.live_adapter(policy(allow_source_transmission=False)).invoke({})
    with pytest.raises(ValidationError):
        policy(endpoint="https://unapproved.example/v1/messages")
