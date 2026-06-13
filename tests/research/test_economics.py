"""Tests for conservative FRED-backed economics research fetcher."""

from datetime import datetime, timezone

import httpx
import pytest

from kal_predict.models import MarketSnapshot
from kal_predict.research.economics import EconomicsResearchFetcher
from kal_predict.research.source_cache import SourceCache

NOW = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)


def make_market(title: str, ticker: str = "ECON-MARKET") -> MarketSnapshot:
    return MarketSnapshot(
        market_id=ticker,
        ticker=ticker,
        title=title,
        timestamp=NOW.isoformat(),
        yes_bid=0.40,
        yes_ask=0.42,
        no_bid=0.58,
        no_ask=0.60,
        volume=1000,
        status="open",
    )


def make_fetcher(handler, api_key: str | None = "fred-key") -> EconomicsResearchFetcher:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.stlouisfed.org",
    )
    return EconomicsResearchFetcher(http_client=client, fred_api_key=api_key, now=lambda: NOW)


def make_cached_fetcher(
    handler,
    tmp_path,
    api_key: str | None = "fred-key",
) -> EconomicsResearchFetcher:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.stlouisfed.org",
    )
    cache = SourceCache(tmp_path / "paper.db", now=lambda: NOW.isoformat())
    return EconomicsResearchFetcher(
        http_client=client,
        fred_api_key=api_key,
        now=lambda: NOW,
        source_cache=cache,
    )


@pytest.mark.asyncio
async def test_economics_fetcher_maps_cpi_threshold_market_to_fred_series():
    requested_series = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_series.append(request.url.params["series_id"])
        return httpx.Response(
            200,
            json={
                "observations": [
                    {"date": "2026-04-01", "value": "319.8"},
                    {"date": "2026-05-01", "value": "321.2"},
                ]
            },
        )

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will CPI be above 320 in May?")
    )

    assert requested_series == ["CPIAUCSL"]
    assert snapshot.usable is True
    assert snapshot.category == "economics"
    assert snapshot.metadata["series_id"] == "CPIAUCSL"
    assert snapshot.metadata["indicator"] == "cpi"
    assert snapshot.metadata["threshold"] == 320.0
    assert snapshot.metadata["latest_value"] == 321.2
    assert snapshot.metadata["prior_value"] == 319.8
    assert snapshot.signals[0].source == "FRED"
    assert snapshot.signals[0].direction == "YES"


@pytest.mark.asyncio
async def test_economics_fetcher_uses_source_cache_on_second_fetch(tmp_path):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={
                "observations": [
                    {"date": "2026-04-01", "value": "319.8"},
                    {"date": "2026-05-01", "value": "321.2"},
                ]
            },
        )
    fetcher = make_cached_fetcher(handler, tmp_path)
    market = make_market("Will CPI be above 320 in May?")

    first = await fetcher.fetch(market)
    second = await fetcher.fetch(market)

    assert first.usable is True
    assert second.usable is True
    assert second.source_health[0].source == "FRED"
    assert request_count == 1


@pytest.mark.asyncio
async def test_economics_fetcher_maps_unemployment_threshold_market_to_fred_series():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["series_id"] == "UNRATE"
        return httpx.Response(
            200,
            json={
                "observations": [
                    {"date": "2026-04-01", "value": "4.1"},
                    {"date": "2026-05-01", "value": "4.3"},
                ]
            },
        )

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will the unemployment rate be above 4.2% in May?")
    )

    assert snapshot.usable is True
    assert snapshot.metadata["series_id"] == "UNRATE"
    assert snapshot.metadata["indicator"] == "unemployment"
    assert snapshot.signals[0].direction == "YES"


@pytest.mark.asyncio
async def test_economics_fetcher_skips_ambiguous_inflation_without_threshold():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("FRED should not be called for ambiguous inflation markets")

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will inflation be higher in May?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "threshold_cannot_be_parsed"
    assert snapshot.source_health == []


@pytest.mark.asyncio
async def test_economics_fetcher_skips_ambiguous_series_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("FRED should not be called for ambiguous series mappings")

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will CPI and GDP both be above 320 in May?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "fred_series_mapping_ambiguous"
    assert snapshot.source_health == []


@pytest.mark.asyncio
async def test_economics_fetcher_missing_fred_api_key_skips_without_crashing():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("FRED should not be called without an API key")

    snapshot = await make_fetcher(handler, api_key=None).fetch(
        make_market("Will CPI be above 320 in May?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "missing_fred_api_key"
    assert snapshot.source_health == []


@pytest.mark.asyncio
async def test_economics_fetcher_fred_timeout_skips_without_uncaught_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("FRED timed out")

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will CPI be above 320 in May?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "source_failure_fred_timeout"
    assert snapshot.source_health[0].source == "FRED"
    assert snapshot.source_health[0].status == "failed"
    assert snapshot.source_health[0].error_code == "timeout"
