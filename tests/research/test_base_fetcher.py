"""Tests for shared research fetcher outage behavior."""

import pytest

from kal_predict.models import MarketSnapshot
from kal_predict.research.base import BaseResearchFetcher


class OutageResearchFetcher(BaseResearchFetcher):
    category_name = "weather"
    min_edge_threshold = 0.05

    async def _fetch_unsafe(self, market: MarketSnapshot):
        raise TimeoutError("NWS timed out")


def make_market() -> MarketSnapshot:
    return MarketSnapshot(
        market_id="WEATHER-RAIN",
        ticker="WEATHER-RAIN",
        title="Will NYC get rain tomorrow?",
        timestamp="2026-06-08T12:00:00Z",
        yes_bid=0.40,
        yes_ask=0.42,
        no_bid=0.58,
        no_ask=0.60,
        volume=1000,
        status="open",
    )


@pytest.mark.asyncio
async def test_source_outage_returns_unusable_snapshot_without_uncaught_exception():
    fetcher = OutageResearchFetcher()

    snapshot = await fetcher.fetch(make_market())

    assert snapshot.usable is False
    assert snapshot.skip_reason == "source_failure_weather_timeout"
    assert snapshot.evidence_items == []
    assert snapshot.signals == []
    assert snapshot.source_health[0].source == "weather"
    assert snapshot.source_health[0].status == "failed"
    assert snapshot.source_health[0].error_code == "timeout"
