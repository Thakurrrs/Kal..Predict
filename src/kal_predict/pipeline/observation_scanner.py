"""Read-only observation scanner.

Instrumentation only: scans real (or mock) markets, classifies each via the
deterministic router, and records what was seen into the durable observations
table. It makes NO decisions, places NO fills, and calls NO external research
sources. Its sole purpose is to accumulate volume/coverage data so the Phase 4
throughput report can answer "how many markets per category per day".
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from kal_predict.adapters.market import MarketDataProvider
from kal_predict.logging_setup import get_logger
from kal_predict.models import MarketSnapshot
from kal_predict.research.router import MarketCategoryRouter
from kal_predict.storage.paper_store import PaperStore

logger = get_logger(__name__)


def _hours_to_close(close_time: Optional[str], now: datetime) -> Optional[float]:
    """Compute hours until close, or None if close_time is missing/unparsable."""
    if not close_time:
        return None
    try:
        parsed = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = (parsed - now).total_seconds() / 3600.0
    return round(delta, 4)


class ObservationScanner:
    """Classify-only scanner that records market observations."""

    def __init__(
        self,
        provider: MarketDataProvider,
        store: PaperStore,
        router: Optional[MarketCategoryRouter] = None,
    ) -> None:
        self._provider = provider
        self._store = store
        self._router = router or MarketCategoryRouter()

    def _build_observation(
        self, scan_id: str, snapshot: MarketSnapshot, observed_at: str, now: datetime
    ) -> dict[str, Any]:
        classification = self._router.classify(snapshot)
        return {
            "scan_id": scan_id,
            "market_id": snapshot.market_id,
            "category": classification.category,
            "subcategory": classification.subcategory,
            "parser_status": classification.parser_status.value,
            "enabled_for_paper": classification.enabled_for_paper,
            "market_implied_prob": round(snapshot.yes_mid, 6),
            "spread": round(snapshot.spread, 6),
            "volume": snapshot.volume,
            "liquidity": snapshot.liquidity,
            "close_time": snapshot.close_time,
            "hours_to_close": _hours_to_close(snapshot.close_time, now),
            "market_status": snapshot.status,
            "observed_at": observed_at,
        }

    async def scan(self, max_markets: int = 100) -> dict[str, Any]:
        """Run one observation pass over up to ``max_markets`` markets.

        Returns a summary of the scan; persists one observation row per market
        (idempotent per scan_id + market_id).
        """
        scan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        observed_at = now.isoformat()

        market_ids = await self._provider.list_markets()
        inserted = 0
        ignored = 0
        seen = 0

        for market_id in market_ids[:max_markets]:
            snapshot = await self._provider.get_market_snapshot(market_id)
            if snapshot is None:
                continue
            seen += 1
            observation = self._build_observation(scan_id, snapshot, observed_at, now)
            write_status = self._store.record_observation(observation)
            if write_status == "inserted":
                inserted += 1
            else:
                ignored += 1

        logger.info(
            "Observation scan complete",
            extra={
                "event_type": "observation_scan",
                "actor": "observation_scanner",
                "scan_id": scan_id,
                "markets_seen": seen,
                "observations_inserted": inserted,
                "observations_ignored": ignored,
            },
        )
        return {
            "scan_id": scan_id,
            "observed_at": observed_at,
            "markets_seen": seen,
            "observations_inserted": inserted,
            "observations_ignored": ignored,
        }
