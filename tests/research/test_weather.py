"""Tests for conservative weather research fetcher."""

from datetime import datetime, timezone

import httpx
import pytest

from kal_predict.models import MarketSnapshot
from kal_predict.research.source_cache import SourceCache
from kal_predict.research.weather import WeatherResearchFetcher

NOW = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)


def make_market(title: str, close_time: str = "2026-06-09T12:00:00+00:00") -> MarketSnapshot:
    return MarketSnapshot(
        market_id="WEATHER-NYC-RAIN",
        ticker="WEATHER-NYC-RAIN",
        title=title,
        timestamp=NOW.isoformat(),
        yes_bid=0.40,
        yes_ask=0.42,
        no_bid=0.58,
        no_ask=0.60,
        volume=1000,
        status="open",
        close_time=close_time,
    )


def make_fetcher(handler) -> WeatherResearchFetcher:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.weather.gov",
    )
    return WeatherResearchFetcher(http_client=client, now=lambda: NOW)


def make_cached_fetcher(handler, tmp_path) -> WeatherResearchFetcher:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.weather.gov",
    )
    cache = SourceCache(tmp_path / "paper.db", now=lambda: NOW.isoformat())
    return WeatherResearchFetcher(http_client=client, now=lambda: NOW, source_cache=cache)


@pytest.mark.asyncio
async def test_weather_fetcher_creates_usable_rain_research():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/points/40.7128,-74.0060":
            return httpx.Response(
                200,
                json={"properties": {"forecastHourly": "https://api.weather.gov/gridpoints/OKX/33,37/forecast/hourly"}},
            )
        return httpx.Response(
            200,
            json={
                "properties": {
                    "generatedAt": "2026-06-08T11:30:00+00:00",
                    "periods": [
                        {
                            "startTime": "2026-06-09T10:00:00+00:00",
                            "endTime": "2026-06-09T11:00:00+00:00",
                            "probabilityOfPrecipitation": {"value": 70},
                        }
                    ],
                }
            },
        )
    fetcher = make_fetcher(handler)

    snapshot = await fetcher.fetch(
        make_market("Will NYC get at least 0.10 inches of rain by Tuesday?")
    )

    assert snapshot.usable is True
    assert snapshot.skip_reason is None
    assert snapshot.category == "weather"
    assert snapshot.metadata["location"] == "nyc"
    assert snapshot.metadata["metric"] == "rain"
    assert snapshot.metadata["threshold_inches"] == 0.10
    assert snapshot.signals[0].direction == "YES"
    assert snapshot.signals[0].source == "NWS"
    assert snapshot.source_health[0].source == "NWS"
    assert snapshot.source_health[0].status == "ok"


@pytest.mark.asyncio
async def test_weather_fetcher_uses_source_cache_on_second_fetch(tmp_path):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request.url.path == "/points/40.7128,-74.0060":
            return httpx.Response(
                200,
                json={
                    "properties": {
                        "forecastHourly": (
                            "https://api.weather.gov/gridpoints/OKX/33,37/forecast/hourly"
                        )
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "properties": {
                    "generatedAt": "2026-06-08T11:30:00+00:00",
                    "periods": [
                        {
                            "startTime": "2026-06-09T10:00:00+00:00",
                            "endTime": "2026-06-09T11:00:00+00:00",
                            "probabilityOfPrecipitation": {"value": 70},
                        }
                    ],
                }
            },
        )
    fetcher = make_cached_fetcher(handler, tmp_path)
    market = make_market("Will NYC get at least 0.10 inches of rain by Tuesday?")

    first = await fetcher.fetch(market)
    second = await fetcher.fetch(market)

    assert first.usable is True
    assert second.usable is True
    assert second.source_health[0].source == "NWS"
    assert request_count == 2


@pytest.mark.asyncio
async def test_weather_fetcher_skips_invalid_threshold_without_calling_nws():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("NWS should not be called when threshold parsing fails")

    snapshot = await make_fetcher(handler).fetch(make_market("Will NYC get rain by Tuesday?"))

    assert snapshot.usable is False
    assert snapshot.skip_reason == "threshold_cannot_be_parsed"
    assert snapshot.source_health == []


@pytest.mark.asyncio
async def test_weather_fetcher_skips_unsupported_location_without_calling_nws():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("NWS should not be called for unsupported locations")

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will Boston get at least 0.10 inches of rain by Tuesday?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "unsupported_location"
    assert snapshot.source_health == []


@pytest.mark.asyncio
async def test_weather_fetcher_skips_nws_gridpoint_lookup_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will NYC get at least 0.10 inches of rain by Tuesday?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "nws_gridpoint_lookup_failed"
    assert snapshot.source_health[0].status == "failed"
    assert snapshot.source_health[0].error_code == "gridpoint_lookup_failed"


@pytest.mark.asyncio
async def test_cached_weather_fetcher_preserves_gridpoint_lookup_failure(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    snapshot = await make_cached_fetcher(handler, tmp_path).fetch(
        make_market("Will NYC get at least 0.10 inches of rain by Tuesday?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "nws_gridpoint_lookup_failed"
    assert snapshot.source_health[0].status == "failed"
    assert snapshot.source_health[0].error_code == "gridpoint_lookup_failed"


@pytest.mark.asyncio
async def test_weather_fetcher_skips_forecast_horizon_beyond_reliable_range():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("NWS should not be called beyond reliable forecast horizon")

    snapshot = await make_fetcher(handler).fetch(
        make_market(
            "Will NYC get at least 0.10 inches of rain by next week?",
            close_time="2026-06-20T12:00:00+00:00",
        )
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "forecast_horizon_beyond_reliable_range"
    assert snapshot.source_health == []


@pytest.mark.asyncio
async def test_weather_fetcher_skips_stale_forecast():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/points/40.7128,-74.0060":
            return httpx.Response(
                200,
                json={"properties": {"forecastHourly": "https://api.weather.gov/gridpoints/OKX/33,37/forecast/hourly"}},
            )
        return httpx.Response(
            200,
            json={
                "properties": {
                    "generatedAt": "2026-06-07T00:00:00+00:00",
                    "periods": [],
                }
            },
        )

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will NYC get at least 0.10 inches of rain by Tuesday?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "forecast_stale"
    assert snapshot.source_health[0].status == "degraded"


@pytest.mark.asyncio
async def test_weather_fetcher_nws_timeout_skips_without_uncaught_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        raise TimeoutError("NWS timed out")

    snapshot = await make_fetcher(handler).fetch(
        make_market("Will NYC get at least 0.10 inches of rain by Tuesday?")
    )

    assert snapshot.usable is False
    assert snapshot.skip_reason == "source_failure_nws_timeout"
    assert snapshot.source_health[0].source == "NWS"
    assert snapshot.source_health[0].status == "failed"
    assert snapshot.source_health[0].error_code == "timeout"
