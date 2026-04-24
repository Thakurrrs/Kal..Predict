"""UI data service regression tests for inference visibility."""

import pytest

from kal_predict.config import AppConfig
from kal_predict.services.inference import InferenceResult
from kal_predict.services.ui_data import UIDataService


@pytest.mark.asyncio
async def test_trial_markets_includes_fallback_visibility() -> None:
    service = UIDataService(AppConfig())

    def fake_fallback(**_kwargs):
        return InferenceResult(
            probability=0.42,
            source="fallback",
            model="qwen2.5-coder:7b",
            raw="",
            parse_ok=False,
            fallback_reason="malformed_output_json",
            latency_ms=7,
            role="hands",
        )

    service._inference.posterior_probability = fake_fallback  # type: ignore[method-assign]
    payload = await service.trial_markets(limit=1)
    assert payload["markets"]
    first = payload["markets"][0]
    assert first["inference_source"] == "fallback"
    assert first["inference_fallback_reason"] == "malformed_output_json"
    assert first["inference_latency_ms"] == 7
