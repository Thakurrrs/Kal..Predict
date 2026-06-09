"""Conservative sports research fetcher.

Sports is observation-only by default. This fetcher only structures narrow
World Cup soccer match-winner markets and never enables paper trading itself.
"""

from datetime import datetime, timedelta, timezone
import re
import uuid

from kal_predict.models import MarketSnapshot, ResearchSnapshot, Signal, SourceHealth
from kal_predict.research.base import BaseResearchFetcher


class SportsResearchFetcher(BaseResearchFetcher):
    """Observation-only sports research fetcher."""

    category_name = "sports"
    min_edge_threshold = 0.05
    paper_trading_enabled = False

    def _timestamps(self) -> tuple[str, str]:
        retrieved = datetime.now(timezone.utc)
        expires = retrieved + timedelta(minutes=30)
        return retrieved.isoformat(), expires.isoformat()

    def _base_metadata(self) -> dict[str, object]:
        return {"paper_trading_enabled": self.paper_trading_enabled}

    def _snapshot(
        self,
        market: MarketSnapshot,
        usable: bool,
        skip_reason: str | None,
        signals: list[Signal],
        metadata: dict[str, object],
    ) -> ResearchSnapshot:
        retrieved_at, expires_at = self._timestamps()
        return ResearchSnapshot(
            research_snapshot_id=str(uuid.uuid4()),
            market_id=market.market_id,
            category=self.category_name,
            usable=usable,
            skip_reason=skip_reason,
            evidence_items=[],
            signals=signals,
            source_health=[
                SourceHealth(
                    source="sports_parser",
                    status="ok",
                    latency_ms=0,
                    freshness_seconds=0,
                    error_code=None,
                )
            ],
            retrieved_at=retrieved_at,
            expires_at=expires_at,
            metadata=metadata,
        )

    def _parse_match_winner(self, title: str) -> tuple[str, str] | None:
        patterns = (
            r"will\s+(?P<a>[a-z .'-]+?)\s+beat\s+(?P<b>[a-z .'-]+?)\s+in",
            r"will\s+(?P<a>[a-z .'-]+?)\s+defeat\s+(?P<b>[a-z .'-]+?)\s+in",
        )
        for pattern in patterns:
            match = re.search(pattern, title.lower())
            if match:
                return match.group("a").strip().title(), match.group("b").strip().title()
        return None

    async def fetch(self, market: MarketSnapshot) -> ResearchSnapshot:
        """Return observation-only sports research for supported markets."""
        title = market.title.strip()
        normalized = title.lower()
        metadata = self._base_metadata()

        if "world cup" not in normalized:
            return self._snapshot(market, False, "unsupported_competition", [], metadata)

        if any(token in normalized for token in ("score", "goals", "total", "spread")):
            metadata["competition"] = "world cup"
            return self._snapshot(market, False, "unsupported_market_type", [], metadata)

        teams = self._parse_match_winner(title)
        if teams is None:
            metadata["competition"] = "world cup"
            return self._snapshot(market, False, "ambiguous_teams", [], metadata)

        team_a, team_b = teams
        metadata.update(
            {
                "competition": "world cup",
                "market_type": "match_winner",
                "team_a": team_a,
                "team_b": team_b,
            }
        )
        signal = Signal(
            source="sports_parser",
            direction="YES",
            confidence=0.5,
            rationale="Parsed supported World Cup soccer match-winner market.",
        )
        return self._snapshot(market, True, None, [signal], metadata)

    def signals(self, research_snapshot: ResearchSnapshot) -> list[Signal]:
        """Return parser-derived signals."""
        return research_snapshot.signals

