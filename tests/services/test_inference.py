"""Inference service security and fallback behavior tests."""

import json

import pytest

from kal_predict.config import AppConfig
from kal_predict.services.inference import InferenceService


@pytest.fixture
def service() -> InferenceService:
    return InferenceService(AppConfig())


def test_inference_fallback_on_malformed_json(service: InferenceService) -> None:
    service._client.chat = lambda **_: {"message": {"content": "not-json"}}  # type: ignore[attr-defined]
    result = service.posterior_probability("TEST_MARKET", 0.55, [])
    assert result.source == "fallback"
    assert result.parse_ok is False
    assert result.fallback_reason == "malformed_output_json"
    assert 0.0 <= result.probability <= 1.0


def test_inference_fallback_on_missing_probability(service: InferenceService) -> None:
    payload = json.dumps({"not_probability": 0.5})
    service._client.chat = lambda **_: {"message": {"content": payload}}  # type: ignore[attr-defined]
    result = service.posterior_probability("TEST_MARKET", 0.55, [])
    assert result.source == "fallback"
    assert result.parse_ok is False
    assert "missing_probability" in str(result.fallback_reason)


def test_inference_uses_brain_role_model(service: InferenceService) -> None:
    called = {}

    def fake_chat(**kwargs):
        called["model"] = kwargs["model"]
        return {"message": {"content": '{"probability": 0.61}'}}

    service._client.chat = fake_chat  # type: ignore[attr-defined]
    result = service.posterior_probability("TEST_MARKET", 0.55, [], role="brain")
    assert result.source == "ollama"
    assert called["model"] == service._config.ollama.brain_model


def test_health_reports_fallback_rate(service: InferenceService) -> None:
    service._client.chat = lambda **_: {"message": {"content": "bad"}}  # type: ignore[attr-defined]
    service.posterior_probability("TEST_MARKET", 0.55, [])
    health = service.health()
    assert health["total_calls"] >= 1
    assert health["fallback_calls"] >= 1
    assert health["fallback_rate"] > 0
