"""Abstract and concrete market data provider implementations."""

from abc import ABC, abstractmethod
from typing import Optional

from kal_predict.fixtures.replay_sample import load_market_snapshots
from kal_predict.logging_setup import get_logger
from kal_predict.models import MarketSnapshot

logger = get_logger(__name__)


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""

    @abstractmethod
    async def get_market_snapshot(self, market_id: str) -> Optional[MarketSnapshot]:
        """Get the current (latest) market snapshot for a market.

        Args:
            market_id: The Kalshi market ID (e.g., 'WEATHER-24-WV-RAIN-20240624')

        Returns:
            MarketSnapshot if market exists, None otherwise
        """
        pass

    @abstractmethod
    async def list_markets(self) -> list[str]:
        """List all available market IDs.

        Returns:
            List of market IDs available from this provider
        """
        pass

    @abstractmethod
    async def get_historical_snapshots(
        self, market_id: str, start_time: str, end_time: str
    ) -> list[MarketSnapshot]:
        """Get historical market snapshots within a time range.

        Used for replay testing and backtesting.

        Args:
            market_id: The Kalshi market ID
            start_time: ISO8601 timestamp (inclusive)
            end_time: ISO8601 timestamp (inclusive)

        Returns:
            List of MarketSnapshot objects in chronological order,
            empty list if no snapshots in range
        """
        pass


class MockMarketDataProvider(MarketDataProvider):
    """Mock provider that loads from fixture data.

    Used for testing and pre-credential development (before Saturday when
    Kalshi API credentials arrive).
    """

    def __init__(self) -> None:
        """Initialize mock provider by loading fixture snapshots."""
        self._snapshots, self._settlement_data = load_market_snapshots()
        # Build index: market_id -> list of snapshots (in chronological order)
        self._snapshot_index: dict[str, list[MarketSnapshot]] = {}
        for snapshot in self._snapshots:
            if snapshot.market_id not in self._snapshot_index:
                self._snapshot_index[snapshot.market_id] = []
            self._snapshot_index[snapshot.market_id].append(snapshot)

        logger.info(
            "MockMarketDataProvider initialized",
            extra={
                "event_type": "provider_init",
                "actor": "mock_market_provider",
                "market_count": len(self._snapshot_index),
                "snapshot_count": len(self._snapshots),
            },
        )

    async def get_market_snapshot(self, market_id: str) -> Optional[MarketSnapshot]:
        """Get the latest snapshot for a market.

        Args:
            market_id: The market ID

        Returns:
            The most recent MarketSnapshot, or None if market not found
        """
        snapshots = self._snapshot_index.get(market_id)
        if not snapshots:
            return None
        # Return the latest (last in chronological order)
        return snapshots[-1]

    async def list_markets(self) -> list[str]:
        """List all market IDs from fixtures.

        Returns:
            Sorted list of market IDs
        """
        return sorted(self._snapshot_index.keys())

    async def get_historical_snapshots(
        self, market_id: str, start_time: str, end_time: str
    ) -> list[MarketSnapshot]:
        """Get snapshots in time range.

        Args:
            market_id: The market ID
            start_time: ISO8601 timestamp (inclusive)
            end_time: ISO8601 timestamp (inclusive)

        Returns:
            List of snapshots within range, in chronological order
        """
        snapshots = self._snapshot_index.get(market_id, [])
        if not snapshots:
            return []

        # Filter by timestamp (simple string comparison works for ISO8601)
        filtered = [s for s in snapshots if start_time <= s.timestamp <= end_time]
        return filtered


class KalshiMarketDataProvider(MarketDataProvider):
    """Kalshi API provider (read-only stubs until Saturday 2026-04-27).

    The Kalshi API requires:
    - api_key_id: Kalshi API key ID (from credentials)
    - private_key_pem: Kalshi private key in PEM format (from credentials)

    Until Saturday when credentials arrive, all methods return None/[]
    with a warning log. Post-Saturday, implement real API calls using
    signed HTTP requests.
    """

    def __init__(self, api_key_id: str, private_key_pem: str) -> None:
        """Initialize Kalshi provider.

        Args:
            api_key_id: Kalshi API key ID
            private_key_pem: Kalshi private key (PEM format)
        """
        self._api_key_id = api_key_id
        self._private_key_pem = private_key_pem
        logger.warning(
            "Kalshi API not available until Saturday 2026-04-27 (credentials arriving)",
            extra={
                "event_type": "provider_init",
                "actor": "kalshi_market_provider",
            },
        )

    async def get_market_snapshot(self, market_id: str) -> Optional[MarketSnapshot]:
        """Get market snapshot from Kalshi API.

        Disabled until Saturday.

        Args:
            market_id: The market ID

        Returns:
            None (disabled until Saturday)
        """
        logger.warning(
            "Kalshi API not available until Saturday 2026-04-27 (credentials arriving)",
            extra={
                "event_type": "api_call_blocked",
                "actor": "kalshi_market_provider",
                "market_id": market_id,
            },
        )
        return None

    async def list_markets(self) -> list[str]:
        """List markets from Kalshi API.

        Disabled until Saturday.

        Returns:
            Empty list (disabled until Saturday)
        """
        logger.warning(
            "Kalshi API not available until Saturday 2026-04-27 (credentials arriving)",
            extra={
                "event_type": "api_call_blocked",
                "actor": "kalshi_market_provider",
            },
        )
        return []

    async def get_historical_snapshots(
        self, market_id: str, start_time: str, end_time: str
    ) -> list[MarketSnapshot]:
        """Get historical snapshots from Kalshi API.

        Disabled until Saturday.

        Args:
            market_id: The market ID
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Empty list (disabled until Saturday)
        """
        logger.warning(
            "Kalshi API not available until Saturday 2026-04-27 (credentials arriving)",
            extra={
                "event_type": "api_call_blocked",
                "actor": "kalshi_market_provider",
                "market_id": market_id,
                "time_range": f"{start_time} to {end_time}",
            },
        )
        return []
