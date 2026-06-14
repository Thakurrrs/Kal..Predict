"""Abstract and concrete market data provider implementations."""

import base64
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from kal_predict.fixtures.replay_sample import load_market_snapshots
from kal_predict.logging_setup import get_logger
from kal_predict.models import MarketSnapshot

logger = get_logger(__name__)

QueryParamValue = str | int | float | bool | None


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
    """Kalshi API provider for read-only market data.

    The Kalshi API requires:
    - api_key_id: Kalshi API key ID (from credentials)
    - private_key_pem: Kalshi private key in PEM format (from credentials)
    """

    def __init__(
        self,
        api_key_id: str,
        private_key_pem: str,
        base_url: str = "https://external-api.kalshi.com",
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Initialize Kalshi provider.

        Args:
            api_key_id: Kalshi API key ID
            private_key_pem: Kalshi private key (PEM format)
            base_url: Kalshi API host without /trade-api/v2
            http_client: Optional injected async HTTP client for tests
        """
        self._api_key_id = api_key_id
        self._private_key_pem = private_key_pem
        self._base_url = base_url.rstrip("/")
        self._client = http_client or httpx.AsyncClient(base_url=self._base_url, timeout=20.0)
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("Kalshi private key must be an RSA private key")
        self._private_key: rsa.RSAPrivateKey = private_key
        logger.info(
            "KalshiMarketDataProvider initialized in read-only mode",
            extra={
                "event_type": "provider_init",
                "actor": "kalshi_market_provider",
            },
        )

    def _parse_decimal(self, value: object, default: float = 0.0) -> float:
        if value in (None, ""):
            return default
        if isinstance(value, (str, int, float)):
            return float(value)
        return default

    def _parse_int_decimal(self, value: object, default: int = 0) -> int:
        if value in (None, ""):
            return default
        if isinstance(value, (str, int, float)):
            return int(float(value))
        return default

    def _signed_headers(
        self,
        method: str,
        path: str,
        timestamp_ms: Optional[str] = None,
    ) -> dict[str, str]:
        """Build Kalshi RSA-PSS signed request headers.

        Kalshi signs timestamp + uppercase method + URL path. Query parameters
        are intentionally excluded from the signed text.
        """
        timestamp = timestamp_ms or str(int(time.time() * 1000))
        signed_text = f"{timestamp}{method.upper()}{path}".encode("utf-8")
        signature = self._private_key.sign(
            signed_text,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self._api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("ascii"),
        }

    async def _get(
        self, path: str, params: Optional[dict[str, QueryParamValue]] = None
    ) -> httpx.Response:
        headers = self._signed_headers("GET", path)
        return await self._client.get(path, params=params, headers=headers)

    def _snapshot_from_market(self, market: dict) -> MarketSnapshot:
        ticker = str(market.get("ticker", ""))
        timestamp = str(
            market.get("updated_time")
            or market.get("open_time")
            or datetime.now(timezone.utc).isoformat()
        )
        return MarketSnapshot(
            market_id=ticker,
            ticker=ticker,
            title=str(market.get("title", "")),
            timestamp=timestamp,
            yes_bid=self._parse_decimal(market.get("yes_bid_dollars")),
            yes_ask=self._parse_decimal(market.get("yes_ask_dollars")),
            no_bid=self._parse_decimal(market.get("no_bid_dollars")),
            no_ask=self._parse_decimal(market.get("no_ask_dollars")),
            volume=self._parse_int_decimal(market.get("volume_fp")),
            status=str(market.get("status", "unknown")),
            close_time=market.get("close_time"),
            category_hint=market.get("event_ticker") or market.get("series_ticker"),
            liquidity=(
                self._parse_decimal(market.get("liquidity_dollars"))
                if market.get("liquidity_dollars") is not None
                else None
            ),
        )

    async def list_market_snapshots(
        self, status: str = "open", limit: int = 100
    ) -> list[MarketSnapshot]:
        """List market snapshots from Kalshi read-only market data."""
        response = await self._get(
            path="/trade-api/v2/markets",
            params={"status": status, "limit": limit},
        )
        response.raise_for_status()
        payload = response.json()
        return [self._snapshot_from_market(market) for market in payload.get("markets", [])]

    async def get_market_snapshot(self, market_id: str) -> Optional[MarketSnapshot]:
        """Get market snapshot from Kalshi API.

        Args:
            market_id: The market ID

        Returns: MarketSnapshot when found, otherwise None
        """
        response = await self._get(f"/trade-api/v2/markets/{market_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        market = payload.get("market", payload)
        return self._snapshot_from_market(market)

    async def list_markets(self) -> list[str]:
        """List markets from Kalshi API.

        Returns:
            List of market tickers
        """
        snapshots = await self.list_market_snapshots(status="open")
        return [snapshot.ticker for snapshot in snapshots]

    async def get_orderbook(self, market_id: str) -> dict:
        """Get raw orderbook for a market."""
        response = await self._get(f"/trade-api/v2/markets/{market_id}/orderbook")
        response.raise_for_status()
        return response.json()

    async def get_historical_snapshots(
        self, market_id: str, start_time: str, end_time: str
    ) -> list[MarketSnapshot]:
        """Get historical snapshots from Kalshi API.

        Args:
            market_id: The market ID
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Empty list until a dedicated historical adapter is implemented
        """
        logger.warning(
            "Kalshi historical snapshots are not implemented",
            extra={
                "event_type": "historical_snapshots_not_implemented",
                "actor": "kalshi_market_provider",
                "market_id": market_id,
                "time_range": f"{start_time} to {end_time}",
            },
        )
        return []
