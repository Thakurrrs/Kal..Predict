"""Tests for MarketDataProvider abstract interface and implementations."""

import pytest

from kal_predict.adapters.market import (
    KalshiMarketDataProvider,
    MarketDataProvider,
    MockMarketDataProvider,
)
from kal_predict.models import MarketSnapshot


class TestMarketDataProviderInterface:
    """Test abstract interface is properly defined."""

    def test_market_data_provider_is_abstract(self):
        """Verify MarketDataProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MarketDataProvider()  # type: ignore


@pytest.mark.asyncio
class TestMockMarketDataProvider:
    """Test MockMarketDataProvider fixture-based implementation."""

    @pytest.fixture
    def mock_provider(self):
        """Create a MockMarketDataProvider instance."""
        return MockMarketDataProvider()

    async def test_mock_market_provider_returns_snapshots(self, mock_provider):
        """Verify snapshot returned for known market."""
        # Get list of markets first
        markets = await mock_provider.list_markets()
        assert len(markets) > 0, "Fixtures should contain at least one market"

        # Get snapshot for first market
        market_id = markets[0]
        snapshot = await mock_provider.get_market_snapshot(market_id)

        assert snapshot is not None
        assert isinstance(snapshot, MarketSnapshot)
        assert snapshot.market_id == market_id
        assert 0 <= snapshot.yes_bid <= 1
        assert 0 <= snapshot.yes_ask <= 1
        assert 0 <= snapshot.no_bid <= 1
        assert 0 <= snapshot.no_ask <= 1

    async def test_mock_list_markets(self, mock_provider):
        """Verify list_markets returns all market IDs from fixtures."""
        markets = await mock_provider.list_markets()

        assert isinstance(markets, list)
        assert len(markets) > 0
        # All should be strings
        assert all(isinstance(m, str) for m in markets)

    async def test_mock_historical_snapshots(self, mock_provider):
        """Verify historical snapshots filtered by time range."""
        # Get a market
        markets = await mock_provider.list_markets()
        assert len(markets) > 0

        market_id = markets[0]

        # Get all historical snapshots (large range)
        all_snapshots = await mock_provider.get_historical_snapshots(
            market_id,
            start_time="2000-01-01T00:00:00Z",
            end_time="2099-12-31T23:59:59Z",
        )

        assert isinstance(all_snapshots, list)
        assert len(all_snapshots) > 0

        # All snapshots should be for requested market
        assert all(s.market_id == market_id for s in all_snapshots)

        # All should be valid MarketSnapshot objects
        assert all(isinstance(s, MarketSnapshot) for s in all_snapshots)

        # Should be ordered chronologically
        timestamps = [s.timestamp for s in all_snapshots]
        assert timestamps == sorted(timestamps), "Snapshots should be chronologically ordered"

    async def test_mock_historical_snapshots_time_filtering(self, mock_provider):
        """Verify time range filtering works correctly."""
        markets = await mock_provider.list_markets()
        market_id = markets[0]

        # Get all snapshots
        all_snapshots = await mock_provider.get_historical_snapshots(
            market_id,
            start_time="2000-01-01T00:00:00Z",
            end_time="2099-12-31T23:59:59Z",
        )

        if len(all_snapshots) > 1:
            # Get middle snapshot as reference
            mid_snapshot = all_snapshots[len(all_snapshots) // 2]
            mid_timestamp = mid_snapshot.timestamp

            # Query only snapshots up to mid point
            limited_snapshots = await mock_provider.get_historical_snapshots(
                market_id,
                start_time="2000-01-01T00:00:00Z",
                end_time=mid_timestamp,
            )

            # Should have fewer snapshots
            assert len(limited_snapshots) <= len(all_snapshots)
            # All should be before or at mid_timestamp
            assert all(s.timestamp <= mid_timestamp for s in limited_snapshots)

    async def test_mock_market_not_found(self, mock_provider):
        """Verify returns None for unknown market."""
        snapshot = await mock_provider.get_market_snapshot("NONEXISTENT_MARKET_ID")
        assert snapshot is None

    async def test_mock_empty_range(self, mock_provider):
        """Verify returns empty list for time range with no data."""
        markets = await mock_provider.list_markets()
        market_id = markets[0]

        # Query far future
        snapshots = await mock_provider.get_historical_snapshots(
            market_id,
            start_time="2099-01-01T00:00:00Z",
            end_time="2099-12-31T23:59:59Z",
        )

        assert snapshots == []


@pytest.mark.asyncio
class TestKalshiMarketDataProvider:
    """Test KalshiMarketDataProvider read-only stubs."""

    @pytest.fixture
    def kalshi_provider(self):
        """Create a KalshiMarketDataProvider instance."""
        return KalshiMarketDataProvider(
            api_key_id="test_key_id",
            private_key_pem="test_key_pem",
        )

    async def test_kalshi_read_only_stubs(self, kalshi_provider, caplog):
        """Verify Kalshi returns None/[] with warning (disabled until Saturday)."""
        import logging

        caplog.set_level(logging.WARNING)

        # get_market_snapshot should return None
        result = await kalshi_provider.get_market_snapshot("WEATHER-24-WV-RAIN-20240624")
        assert result is None

        # Check warning was logged
        assert any(
            "Kalshi API not available until Saturday" in record.message for record in caplog.records
        )

    async def test_kalshi_list_markets_empty(self, kalshi_provider, caplog):
        """Verify list_markets returns empty list."""
        import logging

        caplog.set_level(logging.WARNING)

        result = await kalshi_provider.list_markets()
        assert result == []

        # Check warning was logged
        assert any(
            "Kalshi API not available until Saturday" in record.message for record in caplog.records
        )

    async def test_kalshi_historical_snapshots_empty(self, kalshi_provider, caplog):
        """Verify historical snapshots returns empty list."""
        import logging

        caplog.set_level(logging.WARNING)

        result = await kalshi_provider.get_historical_snapshots(
            "WEATHER-24-WV-RAIN-20240624",
            start_time="2024-06-01T00:00:00Z",
            end_time="2024-06-30T23:59:59Z",
        )
        assert result == []

        # Check warning was logged
        assert any(
            "Kalshi API not available until Saturday" in record.message for record in caplog.records
        )
