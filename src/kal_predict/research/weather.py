"""Conservative NWS-backed weather research fetcher."""

import re
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from kal_predict.models import EvidenceItem, MarketSnapshot, ResearchSnapshot, Signal, SourceHealth
from kal_predict.research.base import BaseResearchFetcher
from kal_predict.research.source_cache import SourceCache


class GridpointLookupError(Exception):
    """NWS point lookup could not map a supported location to a forecast grid."""


class WeatherResearchFetcher(BaseResearchFetcher):
    """Fetch deterministic weather evidence from the National Weather Service."""

    category_name = "weather"
    source_name = "NWS"
    min_edge_threshold = 0.05

    _SUPPORTED_LOCATIONS = {
        "nyc": ("40.7128", "-74.0060"),
        "new york city": ("40.7128", "-74.0060"),
        "new york": ("40.7128", "-74.0060"),
    }

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        now=None,
        base_url: str = "https://api.weather.gov",
        max_forecast_age_seconds: int = 6 * 60 * 60,
        max_forecast_horizon_days: int = 7,
        source_cache: SourceCache | None = None,
        nws_cache_ttl_seconds: int = 1800,
    ) -> None:
        self._client = http_client or httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
            headers={"User-Agent": "kal-predict/0.1.0"},
        )
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._max_forecast_age_seconds = max_forecast_age_seconds
        self._max_forecast_horizon = timedelta(days=max_forecast_horizon_days)
        self._source_cache = source_cache
        self._nws_cache_ttl_seconds = nws_cache_ttl_seconds

    async def _fetch_unsafe(self, market: MarketSnapshot) -> ResearchSnapshot:
        parsed = self._parse_market(market)
        if parsed["skip_reason"]:
            return self._snapshot(
                market,
                usable=False,
                skip_reason=parsed["skip_reason"],
                evidence_items=[],
                signals=[],
                source_health=[],
                metadata=parsed["metadata"],
            )

        try:
            forecast_url = await self._forecast_url(parsed["metadata"])
        except GridpointLookupError:
            return self._snapshot(
                market,
                usable=False,
                skip_reason="nws_gridpoint_lookup_failed",
                evidence_items=[],
                signals=[],
                source_health=[
                    self._health("failed", error_code="gridpoint_lookup_failed")
                ],
                metadata=parsed["metadata"],
            )
        forecast = await self._get_json(forecast_url)
        generated_at = self._parse_time(forecast.get("properties", {}).get("generatedAt"))
        if generated_at is None:
            return self._snapshot(
                market,
                usable=False,
                skip_reason="forecast_generated_at_missing",
                evidence_items=[],
                signals=[],
                source_health=[self._health("degraded", error_code="missing_generated_at")],
                metadata=parsed["metadata"],
            )

        freshness_seconds = int((self._now() - generated_at).total_seconds())
        if freshness_seconds > self._max_forecast_age_seconds:
            return self._snapshot(
                market,
                usable=False,
                skip_reason="forecast_stale",
                evidence_items=[],
                signals=[],
                source_health=[self._health("degraded", freshness_seconds=freshness_seconds)],
                metadata=parsed["metadata"],
            )

        period = self._period_for_deadline(
            forecast.get("properties", {}).get("periods", []),
            parsed["deadline"],
        )
        if period is None:
            return self._snapshot(
                market,
                usable=False,
                skip_reason="forecast_horizon_unavailable",
                evidence_items=[],
                signals=[],
                source_health=[self._health("degraded", freshness_seconds=freshness_seconds)],
                metadata=parsed["metadata"],
            )

        probability = period.get("probabilityOfPrecipitation", {}).get("value")
        if probability is None:
            return self._snapshot(
                market,
                usable=False,
                skip_reason="forecast_probability_missing",
                evidence_items=[],
                signals=[],
                source_health=[self._health("degraded", freshness_seconds=freshness_seconds)],
                metadata=parsed["metadata"],
            )

        direction = "YES" if probability >= 50 else "NO"
        confidence = max(0.5, min(0.95, abs(probability - 50) / 100 + 0.5))
        evidence = EvidenceItem(
            evidence_id=str(uuid.uuid4()),
            source="NWS",
            url=forecast_url,
            retrieved_at=self._now().isoformat(),
            event_time=period.get("startTime", parsed["deadline"].isoformat()),
            claim=f"NWS precipitation probability is {probability}%.",
            confidence_hint=confidence,
            reliability_score=0.8,
        )
        signal = Signal(
            source="NWS",
            direction=direction,
            confidence=confidence,
            rationale=f"NWS precipitation probability is {probability}% before market deadline.",
        )
        metadata = {
            **parsed["metadata"],
            "forecast_probability_percent": probability,
        }
        return self._snapshot(
            market,
            usable=True,
            skip_reason=None,
            evidence_items=[evidence],
            signals=[signal],
            source_health=[self._health("ok", freshness_seconds=freshness_seconds)],
            metadata=metadata,
        )

    async def _forecast_url(self, metadata: dict[str, object]) -> str:
        lat, lon = metadata["coordinates"]
        point_path = f"/points/{lat},{lon}"
        if self._source_cache is None:
            response = await self._client.get(point_path)
            if response.status_code >= 400:
                raise GridpointLookupError
            point = response.json()
        else:
            result = await self._source_cache.get_or_fetch(
                source="NWS",
                cache_key=f"points:{lat},{lon}",
                ttl_seconds=self._nws_cache_ttl_seconds,
                fetch=lambda: self._get_point_json(point_path),
            )
            point = result.payload
        forecast_url = point.get("properties", {}).get("forecastHourly")
        if not forecast_url:
            raise GridpointLookupError
        return forecast_url

    async def _get_point_json(self, url: str) -> dict[str, object]:
        response = await self._client.get(url)
        if response.status_code >= 400:
            raise GridpointLookupError
        return response.json()

    async def _get_json(self, url: str) -> dict[str, object]:
        if self._source_cache is not None and "/forecast/hourly" in url:
            result = await self._source_cache.get_or_fetch(
                source="NWS",
                cache_key=f"forecast_hourly:{url}",
                ttl_seconds=self._nws_cache_ttl_seconds,
                fetch=lambda: self._get_uncached_json(url),
            )
            return result.payload
        return await self._get_uncached_json(url)

    async def _get_uncached_json(self, url: str) -> dict[str, object]:
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    def _parse_market(self, market: MarketSnapshot) -> dict[str, object]:
        metadata: dict[str, object] = {"metric": "rain"}
        normalized = market.title.strip().lower()
        location = self._location(normalized)
        if location is None:
            return {"skip_reason": "unsupported_location", "metadata": metadata}
        metadata.update({"location": location[0], "coordinates": location[1]})

        if not any(token in normalized for token in ("rain", "precipitation")):
            return {"skip_reason": "unsupported_weather_metric", "metadata": metadata}

        threshold = self._threshold(normalized)
        if threshold is None:
            return {"skip_reason": "threshold_cannot_be_parsed", "metadata": metadata}
        metadata["threshold_inches"] = threshold

        if not market.close_time:
            return {"skip_reason": "event_time_unmapped", "metadata": metadata}
        deadline = self._parse_time(market.close_time)
        if deadline is None:
            return {"skip_reason": "event_time_unmapped", "metadata": metadata}
        if deadline - self._now() > self._max_forecast_horizon:
            return {
                "skip_reason": "forecast_horizon_beyond_reliable_range",
                "metadata": metadata,
            }

        return {"skip_reason": None, "metadata": metadata, "deadline": deadline}

    def _location(self, normalized_title: str) -> tuple[str, tuple[str, str]] | None:
        for name, coordinates in self._SUPPORTED_LOCATIONS.items():
            if name in normalized_title:
                return "nyc", coordinates
        return None

    def _threshold(self, normalized_title: str) -> float | None:
        match = re.search(
            r"(?:at least|over|above)\s+(?P<amount>\d+(?:\.\d+)?)\s*"
            r"(?:inches|inch|in)",
            normalized_title,
        )
        if not match:
            return None
        return float(match.group("amount"))

    def _period_for_deadline(
        self, periods: list[dict[str, object]], deadline: datetime
    ) -> dict[str, object] | None:
        for period in periods:
            start = self._parse_time(period.get("startTime"))
            if start is not None and start <= deadline:
                return period
        return None

    def _snapshot(
        self,
        market: MarketSnapshot,
        usable: bool,
        skip_reason: str | None,
        evidence_items: list[EvidenceItem],
        signals: list[Signal],
        source_health: list[SourceHealth],
        metadata: dict[str, object],
    ) -> ResearchSnapshot:
        retrieved = self._now()
        expires = retrieved + timedelta(minutes=30)
        metadata = {k: v for k, v in metadata.items() if k != "coordinates"}
        return ResearchSnapshot(
            research_snapshot_id=str(uuid.uuid4()),
            market_id=market.market_id,
            category=self.category_name,
            usable=usable,
            skip_reason=skip_reason,
            evidence_items=evidence_items,
            signals=signals,
            source_health=source_health,
            retrieved_at=retrieved.isoformat(),
            expires_at=expires.isoformat(),
            metadata=metadata,
        )

    def _health(
        self,
        status: str,
        freshness_seconds: int = 0,
        error_code: str | None = None,
    ) -> SourceHealth:
        return SourceHealth(
            source="NWS",
            status=status,
            latency_ms=0,
            freshness_seconds=max(0, freshness_seconds),
            error_code=error_code,
        )

    def _parse_time(self, value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
