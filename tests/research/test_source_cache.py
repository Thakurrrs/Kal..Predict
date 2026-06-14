"""Tests for persistent research source caching."""

import pytest

from kal_predict.research.source_cache import SourceCache


@pytest.mark.asyncio
async def test_source_cache_fetches_and_persists_on_miss(tmp_path):
    cache = SourceCache(tmp_path / "paper.db", now=lambda: "2026-06-09T12:00:00+00:00")
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return {"temperature": 72}

    result = await cache.get_or_fetch(
        source="NWS",
        cache_key="points:nyc",
        ttl_seconds=3600,
        fetch=fetch,
    )

    assert result.payload == {"temperature": 72}
    assert result.cache_hit is False
    assert result.source_health.source == "NWS"
    assert result.source_health.status == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_source_cache_returns_cached_payload_before_expiry(tmp_path):
    cache = SourceCache(tmp_path / "paper.db", now=lambda: "2026-06-09T12:00:00+00:00")
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return {"value": calls}

    first = await cache.get_or_fetch("FRED", "series:CPIAUCSL", 3600, fetch)
    second = await cache.get_or_fetch("FRED", "series:CPIAUCSL", 3600, fetch)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.payload == {"value": 1}
    assert calls == 1


@pytest.mark.asyncio
async def test_source_cache_refreshes_after_expiry(tmp_path):
    current_time = "2026-06-09T12:00:00+00:00"
    cache = SourceCache(tmp_path / "paper.db", now=lambda: current_time)
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return {"value": calls}

    first = await cache.get_or_fetch("FRED", "series:UNRATE", 60, fetch)
    current_time = "2026-06-09T12:02:00+00:00"
    second = await cache.get_or_fetch("FRED", "series:UNRATE", 60, fetch)

    assert first.payload == {"value": 1}
    assert second.payload == {"value": 2}
    assert second.cache_hit is False
    assert calls == 2


@pytest.mark.asyncio
async def test_source_cache_isolates_keys(tmp_path):
    cache = SourceCache(tmp_path / "paper.db", now=lambda: "2026-06-09T12:00:00+00:00")

    async def fetch_cpi():
        return {"series": "CPIAUCSL"}

    async def fetch_unrate():
        return {"series": "UNRATE"}

    cpi = await cache.get_or_fetch("FRED", "series:CPIAUCSL", 3600, fetch_cpi)
    unrate = await cache.get_or_fetch("FRED", "series:UNRATE", 3600, fetch_unrate)

    assert cpi.payload == {"series": "CPIAUCSL"}
    assert unrate.payload == {"series": "UNRATE"}
