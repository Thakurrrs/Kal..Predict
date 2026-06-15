"""UI data service regression tests for inference visibility."""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kal_predict.adapters.market import KalshiMarketDataProvider, MockMarketDataProvider
from kal_predict.config import AppConfig, KalshiConfig, PaperDataConfig
from kal_predict.models import MarketSnapshot
from kal_predict.services.inference import InferenceResult
from kal_predict.services.ui_data import UIDataService, build_market_provider
from kal_predict.storage.paper_store import PaperStore


class StaticMarketProvider(MockMarketDataProvider):
    async def list_markets(self) -> list[str]:
        return ["REAL_MARKET_1"]

    async def get_market_snapshot(self, market_id: str) -> MarketSnapshot | None:
        return MarketSnapshot(
            market_id=market_id,
            ticker=market_id,
            title="Real market title",
            timestamp="2026-06-15T12:00:00+00:00",
            yes_bid=0.42,
            yes_ask=0.45,
            no_bid=0.55,
            no_ask=0.58,
            volume=1234,
            status="open",
            close_time="2026-06-16T12:00:00+00:00",
            category_hint="KXSOC",
            liquidity=2500.0,
        )


def make_private_key_pem() -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def app_config_with_temp_paper_db(tmp_path) -> AppConfig:
    return AppConfig(
        paper_data=PaperDataConfig(database_path=str(tmp_path / "paper.db"))
    )


def test_build_market_provider_falls_back_to_mock_without_credentials() -> None:
    provider, source = build_market_provider(AppConfig())

    assert isinstance(provider, MockMarketDataProvider)
    assert source == "mock_market_provider"


def test_build_market_provider_uses_kalshi_when_credentials_available(tmp_path) -> None:
    key_path = tmp_path / "kalshi_private_key.pem"
    key_path.write_text(make_private_key_pem(), encoding="utf-8")
    config = AppConfig(
        kalshi=KalshiConfig(api_key_id="test-key", private_key_path=str(key_path))
    )

    provider, source = build_market_provider(config)

    assert isinstance(provider, KalshiMarketDataProvider)
    assert source == "kalshi_read_only"


@pytest.mark.asyncio
async def test_markets_response_labels_real_kalshi_read_only_source(tmp_path) -> None:
    service = UIDataService(
        app_config_with_temp_paper_db(tmp_path),
        market_provider=StaticMarketProvider(),
        market_source="kalshi_read_only",
    )

    payload = await service.markets(limit=1)

    assert payload["source"] == "kalshi_read_only"
    assert payload["provider_status"] == "credentialed"
    assert payload["markets"][0]["title"] == "Real market title"
    assert payload["markets"][0]["status"] == "open"
    assert payload["markets"][0]["close_time"] == "2026-06-16T12:00:00+00:00"
    assert payload["markets"][0]["category_hint"] == "KXSOC"
    assert payload["markets"][0]["liquidity"] == 2500.0


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


@pytest.mark.asyncio
async def test_trial_manual_bet_records_durable_decision_and_fill(tmp_path) -> None:
    config = AppConfig(
        paper_data=PaperDataConfig(database_path=str(tmp_path / "paper.db"))
    )
    service = UIDataService(config)

    market_id = (await service.trial_markets(limit=1))["markets"][0]["market_id"]

    result = await service.trial_manual_bet(market_id=market_id, side="YES", contracts=1)

    store = PaperStore(tmp_path / "paper.db")
    assert result["ok"] is True
    assert store.count_rows("decisions") == 1
    assert store.count_rows("paper_fills") == 1


@pytest.mark.asyncio
async def test_paper_metrics_reads_durable_paper_store(tmp_path) -> None:
    config = AppConfig(
        paper_data=PaperDataConfig(database_path=str(tmp_path / "paper.db"))
    )
    service = UIDataService(config)
    market_id = (await service.trial_markets(limit=1))["markets"][0]["market_id"]

    await service.trial_manual_bet(market_id=market_id, side="YES", contracts=2)

    metrics = await service.paper_metrics()

    assert metrics["source"] == "paper_store"
    assert metrics["total_trades"] == 1
    assert metrics["unresolved_exposure"] == result_cost(service)


def result_cost(service: UIDataService) -> float:
    return service._trial_bets[0]["cost_usd"]
