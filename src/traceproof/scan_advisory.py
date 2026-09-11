"""Explicit bounded advisory options for the Joern main workflow."""

from dataclasses import dataclass

from traceproof.domain import TraceProofError
from traceproof.joern_claims import require_policy
from traceproof.models import Adapter, ModelConfig, ReplayAdapter, live_adapter, read_config
from traceproof.persistence import TriageBudget


@dataclass(frozen=True)
class AdvisoryOptions:
    config: ModelConfig
    adapter: Adapter
    key: str
    review_policy: str
    offset: int = 0
    limit: int = 1

    def __post_init__(self):
        require_policy(self.review_policy)
        if not self.key.strip() or len(self.key) > 200:
            raise TraceProofError("Advisory key must contain 1–200 characters")
        if (
            type(self.offset) is not int
            or self.offset < 0
            or type(self.limit) is not int
            or not 1 <= self.limit <= 100
        ):
            raise TraceProofError("Advisory page requires offset >= 0 and limit 1–100")

    def validate_scope(self, language, discovery_profile):
        expected_language, profile, _, _ = require_policy(self.review_policy)
        if language != expected_language or (discovery_profile or "default") != profile:
            raise TraceProofError(
                f"Scan advisory policy requires Joern {expected_language} profile {profile}"
            )

    def validate_budget(self, store, run_id):
        with store.transaction() as session:
            if session.get(TriageBudget, run_id) is None:
                raise TraceProofError("Configure the run triage budget before advisory scanning")


class CountingAdapter:
    def __init__(self, delegate):
        self.delegate = delegate
        self.identity = delegate.identity
        self.calls = 0

    def invoke(self, body):
        self.calls += 1
        return self.delegate.invoke(body)


def run_advisory(store, repo_id, attempt_id, options):
    from traceproof.batch_triage import triage_attempt

    adapter = CountingAdapter(options.adapter)
    try:
        result = triage_attempt(
            store,
            repo_id,
            attempt_id,
            options.config,
            adapter,
            options.key,
            options.offset,
            options.limit,
            review_policy=options.review_policy,
        )
    except TraceProofError as exc:
        result = {"status": "halted", "reason": str(exc)}
    return {
        **result,
        "review_policy": options.review_policy,
        "provider": options.config.provider,
        "provider_invocations": adapter.calls,
        "live_model_calls": 0 if options.config.provider == "replay" else adapter.calls,
        "simulated": options.config.provider == "replay",
    }


def load_advisory(config_path, review_policy, key, replay, offset=0, limit=1):
    """CLI parsing only; never invokes a provider or sets a budget implicitly."""
    if config_path is None:
        if any(v is not None for v in (review_policy, key, replay)) or offset != 0 or limit != 1:
            raise TraceProofError("Advisory options require --advisory-config")
        return None
    if review_policy is None or key is None:
        raise TraceProofError("Advisory scanning requires --review-policy and --advisory-key")
    config = read_config(config_path)
    if config.provider == "replay":
        if replay is None:
            raise TraceProofError("Replay advisory requires --replay RESPONSE_JSON")
        adapter = ReplayAdapter(replay)
    else:
        if replay is not None:
            raise TraceProofError("A live advisory cannot use a replay fixture")
        adapter = live_adapter(config)
    return AdvisoryOptions(config, adapter, key, review_policy, offset, limit)
