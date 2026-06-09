"""Conservative FRED-backed economics research fetcher."""

import re
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from kal_predict.models import EvidenceItem, MarketSnapshot, ResearchSnapshot, Signal, SourceHealth
from kal_predict.research.base import BaseResearchFetcher


class EconomicsResearchFetcher(BaseResearchFetcher):
    """Fetch deterministic economic evidence from official FRED series."""

    category_name = "economics"
    source_name = "FRED"
    min_edge_threshold = 0.05

    _SERIES = {
        "cpi": ("CPIAUCSL", ("cpi", "consumer price index", "inflation")),
        "unemployment": ("UNRATE", ("unemployment", "jobless rate")),
        "fed_funds": ("FEDFUNDS", ("fed funds", "federal funds", "interest rate", "rates")),
        "gdp": ("GDP", ("gdp", "gross domestic product")),
    }

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        fred_api_key: str | None = None,
        now=None,
        base_url: str = "https://api.stlouisfed.org",
    ) -> None:
        self._client = http_client or httpx.AsyncClient(base_url=base_url, timeout=20.0)
        self._fred_api_key = fred_api_key
        self._now = now or (lambda: datetime.now(timezone.utc))

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

        if not self._fred_api_key:
            return self._snapshot(
                market,
                usable=False,
                skip_reason="missing_fred_api_key",
                evidence_items=[],
                signals=[],
                source_health=[],
                metadata=parsed["metadata"],
            )

        observations = await self._fetch_observations(parsed["metadata"]["series_id"])
        values = self._numeric_observations(observations)
        if len(values) < 2:
            return self._snapshot(
                market,
                usable=False,
                skip_reason="latest_official_observation_unavailable",
                evidence_items=[],
                signals=[],
                source_health=[self._health("degraded", error_code="insufficient_observations")],
                metadata=parsed["metadata"],
            )

        prior = values[-2]
        latest = values[-1]
        comparison = parsed["metadata"]["comparison"]
        threshold = parsed["metadata"]["threshold"]
        if comparison == "above":
            yes_direction = latest["value"] > threshold
        else:
            yes_direction = latest["value"] < threshold
        trend = latest["value"] - prior["value"]
        confidence = self._confidence(latest["value"], threshold)
        signal = Signal(
            source="FRED",
            direction="YES" if yes_direction else "NO",
            confidence=confidence,
            rationale=(
                f"Latest official {parsed['metadata']['series_id']} observation is "
                f"{latest['value']} versus threshold {threshold}."
            ),
        )
        evidence = EvidenceItem(
            evidence_id=str(uuid.uuid4()),
            source="FRED",
            url="/fred/series/observations",
            retrieved_at=self._now().isoformat(),
            event_time=latest["date"],
            claim=f"Latest {parsed['metadata']['series_id']} value is {latest['value']}.",
            confidence_hint=confidence,
            reliability_score=0.9,
        )
        metadata = {
            **parsed["metadata"],
            "latest_value": latest["value"],
            "latest_observation_date": latest["date"],
            "prior_value": prior["value"],
            "prior_observation_date": prior["date"],
            "recent_trend": trend,
            "release_calendar": "fred_observation_dates",
        }
        return self._snapshot(
            market,
            usable=True,
            skip_reason=None,
            evidence_items=[evidence],
            signals=[signal],
            source_health=[self._health("ok", freshness_seconds=self._freshness(latest["date"]))],
            metadata=metadata,
        )

    async def _fetch_observations(self, series_id: str) -> list[dict[str, str]]:
        response = await self._client.get(
            "/fred/series/observations",
            params={
                "series_id": series_id,
                "api_key": self._fred_api_key,
                "file_type": "json",
                "sort_order": "asc",
            },
        )
        response.raise_for_status()
        return response.json().get("observations", [])

    def _parse_market(self, market: MarketSnapshot) -> dict[str, object]:
        metadata: dict[str, object] = {}
        normalized = market.title.strip().lower()
        indicator_result = self._indicator(normalized)
        if indicator_result["status"] == "ambiguous":
            return {"skip_reason": "fred_series_mapping_ambiguous", "metadata": metadata}
        indicator = indicator_result["indicator"]
        if indicator is None:
            return {"skip_reason": "unsupported_economic_indicator", "metadata": metadata}

        threshold = self._threshold(normalized)
        if threshold is None:
            metadata["indicator"] = indicator
            metadata["series_id"] = self._SERIES[indicator][0]
            return {"skip_reason": "threshold_cannot_be_parsed", "metadata": metadata}

        metadata.update(
            {
                "indicator": indicator,
                "series_id": self._SERIES[indicator][0],
                "threshold": threshold,
                "comparison": self._comparison(normalized),
            }
        )
        return {"skip_reason": None, "metadata": metadata}

    def _indicator(self, normalized_title: str) -> dict[str, str | None]:
        matched = [
            indicator
            for indicator, (_, keywords) in self._SERIES.items()
            if any(self._keyword_matches(normalized_title, keyword) for keyword in keywords)
        ]
        if len(matched) == 1:
            return {"status": "ok", "indicator": matched[0]}
        if len(matched) > 1:
            return {"status": "ambiguous", "indicator": None}
        return {"status": "unsupported", "indicator": None}

    def _keyword_matches(self, title: str, keyword: str) -> bool:
        escaped = re.escape(keyword)
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", title) is not None

    def _threshold(self, normalized_title: str) -> float | None:
        match = re.search(
            r"(?:above|over|at least|below|under|less than)\s+"
            r"(?P<amount>\d+(?:\.\d+)?)\s*%?",
            normalized_title,
        )
        if not match:
            return None
        return float(match.group("amount"))

    def _comparison(self, normalized_title: str) -> str:
        if any(token in normalized_title for token in ("below", "under", "less than")):
            return "below"
        return "above"

    def _numeric_observations(
        self, observations: list[dict[str, str]]
    ) -> list[dict[str, float | str]]:
        values = []
        for observation in observations:
            try:
                value = float(observation["value"])
            except (KeyError, TypeError, ValueError):
                continue
            values.append({"date": observation.get("date", ""), "value": value})
        return values

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
            source="FRED",
            status=status,
            latency_ms=0,
            freshness_seconds=max(0, freshness_seconds),
            error_code=error_code,
        )

    def _freshness(self, date_value: str) -> int:
        try:
            observed = datetime.fromisoformat(date_value).replace(tzinfo=timezone.utc)
        except ValueError:
            return 0
        return int((self._now() - observed).total_seconds())

    def _confidence(self, latest_value: float, threshold: float) -> float:
        if threshold == 0:
            return 0.5
        distance = abs(latest_value - threshold) / abs(threshold)
        return max(0.5, min(0.95, 0.5 + distance))
