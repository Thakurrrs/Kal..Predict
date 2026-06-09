"""Base interfaces for category-specific research fetchers."""

import uuid
from abc import ABC
from datetime import datetime, timezone

from kal_predict.models import MarketSnapshot, ResearchSnapshot, Signal, SourceHealth


class BaseResearchFetcher(ABC):
    """Abstract interface for category research fetchers."""

    category_name: str
    min_edge_threshold: float
    source_name: str | None = None

    async def fetch(self, market: MarketSnapshot) -> ResearchSnapshot:
        """Fetch research, converting source outages into unusable snapshots."""
        try:
            return await self._fetch_unsafe(market)
        except Exception as exc:
            return self._source_failure_snapshot(market, exc)

    async def _fetch_unsafe(self, market: MarketSnapshot) -> ResearchSnapshot:
        """Fetch or derive research for a market without shared outage handling."""
        raise NotImplementedError

    def signals(self, research_snapshot: ResearchSnapshot) -> list[Signal]:
        """Return directional signals from a research snapshot."""
        return research_snapshot.signals

    def _source_failure_snapshot(
        self, market: MarketSnapshot, exc: Exception
    ) -> ResearchSnapshot:
        retrieved_at = datetime.now(timezone.utc).isoformat()
        error_code = self._error_code(exc)
        return ResearchSnapshot(
            research_snapshot_id=str(uuid.uuid4()),
            market_id=market.market_id,
            category=self.category_name,
            usable=False,
            skip_reason=f"source_failure_{self._source_key()}_{error_code}",
            evidence_items=[],
            signals=[],
            source_health=[
                SourceHealth(
                    source=self.source_name or self.category_name,
                    status="failed",
                    latency_ms=0,
                    freshness_seconds=0,
                    error_code=error_code,
                )
            ],
            retrieved_at=retrieved_at,
            expires_at=retrieved_at,
            metadata={"error_type": exc.__class__.__name__},
        )

    def _error_code(self, exc: Exception) -> str:
        if isinstance(exc, TimeoutError) or "timeout" in exc.__class__.__name__.lower():
            return "timeout"
        return "source_error"

    def _source_key(self) -> str:
        return (self.source_name or self.category_name).lower()
