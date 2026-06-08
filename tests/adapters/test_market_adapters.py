"""Tests for MarketDataProvider abstract interface and implementations."""

import base64

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

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
    """Test KalshiMarketDataProvider read-only API behavior."""

    @pytest.fixture
    def rsa_private_key_pem(self) -> str:
        """Create a valid RSA private key for signing tests."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

    @pytest.fixture
    def kalshi_provider(self, rsa_private_key_pem):
        """Create a KalshiMarketDataProvider instance."""
        return KalshiMarketDataProvider(
            api_key_id="test_key_id",
            private_key_pem=rsa_private_key_pem,
        )

    async def test_kalshi_signed_headers_are_rsa_pss_sha256(self, rsa_private_key_pem):
        """Signed headers follow Kalshi timestamp + method + path convention."""
        provider = KalshiMarketDataProvider(
            api_key_id="test_key_id",
            private_key_pem=rsa_private_key_pem,
        )

        headers = provider._signed_headers(
            method="GET",
            path="/trade-api/v2/markets",
            timestamp_ms="1790000000000",
        )

        assert headers["KALSHI-ACCESS-KEY"] == "test_key_id"
        assert headers["KALSHI-ACCESS-TIMESTAMP"] == "1790000000000"
        assert "KALSHI-ACCESS-SIGNATURE" in headers

        private_key = serialization.load_pem_private_key(
            rsa_private_key_pem.encode("utf-8"),
            password=None,
        )
        public_key = private_key.public_key()
        signature = base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"])
        public_key.verify(
            signature,
            b"1790000000000GET/trade-api/v2/markets",
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )

    async def test_kalshi_requests_include_signed_headers(self, rsa_private_key_pem):
        """Read-only API requests include Kalshi auth headers."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["KALSHI-ACCESS-KEY"] == "test_key_id"
            assert request.headers["KALSHI-ACCESS-TIMESTAMP"].isdigit()
            assert request.headers["KALSHI-ACCESS-SIGNATURE"]
            return httpx.Response(200, json={"markets": [], "cursor": ""})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://external-api.kalshi.com",
        ) as client:
            provider = KalshiMarketDataProvider(
                api_key_id="test_key_id",
                private_key_pem=rsa_private_key_pem,
                http_client=client,
                base_url="https://external-api.kalshi.com",
            )
            snapshots = await provider.list_market_snapshots(status="open")

        assert snapshots == []

    async def test_kalshi_list_market_snapshots_maps_api_response(self, rsa_private_key_pem):
        """Verify Kalshi market JSON maps into richer MarketSnapshot records."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/trade-api/v2/markets"
            assert request.url.params["status"] == "open"
            return httpx.Response(
                200,
                json={
                    "markets": [
                        {
                            "ticker": "KXCPICORE-26JUN-T3.0",
                            "title": "Will core CPI inflation be above 3.0% in June 2026?",
                            "status": "open",
                            "close_time": "2026-06-10T14:00:00Z",
                            "yes_bid_dollars": "0.4100",
                            "yes_ask_dollars": "0.4400",
                            "no_bid_dollars": "0.5600",
                            "no_ask_dollars": "0.5900",
                            "volume_fp": "4200.00",
                            "liquidity_dollars": "120.5000",
                            "event_ticker": "KXCPICORE-26JUN",
                        }
                    ],
                    "cursor": "",
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://external-api.kalshi.com",
        ) as client:
            provider = KalshiMarketDataProvider(
                api_key_id="test_key_id",
                private_key_pem=rsa_private_key_pem,
                http_client=client,
                base_url="https://external-api.kalshi.com",
            )
            snapshots = await provider.list_market_snapshots(status="open")

        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.market_id == "KXCPICORE-26JUN-T3.0"
        assert snapshot.ticker == "KXCPICORE-26JUN-T3.0"
        assert snapshot.title.startswith("Will core CPI")
        assert snapshot.status == "open"
        assert snapshot.yes_bid == 0.41
        assert snapshot.yes_ask == 0.44
        assert snapshot.no_bid == 0.56
        assert snapshot.no_ask == 0.59
        assert snapshot.volume == 4200
        assert snapshot.liquidity == 120.5

    async def test_kalshi_list_markets_returns_tickers_from_api(self, rsa_private_key_pem):
        """Existing list_markets API remains compatible and returns ticker strings."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "markets": [
                        {
                            "ticker": "MARKET-1",
                            "title": "Market 1",
                            "status": "open",
                            "yes_bid_dollars": "0.4000",
                            "yes_ask_dollars": "0.4500",
                            "no_bid_dollars": "0.5500",
                            "no_ask_dollars": "0.6000",
                            "volume_fp": "10.00",
                        }
                    ],
                    "cursor": "",
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://external-api.kalshi.com",
        ) as client:
            provider = KalshiMarketDataProvider(
                api_key_id="test_key_id",
                private_key_pem=rsa_private_key_pem,
                http_client=client,
                base_url="https://external-api.kalshi.com",
            )
            markets = await provider.list_markets()

        assert markets == ["MARKET-1"]

    async def test_kalshi_get_market_snapshot_fetches_single_market(self, rsa_private_key_pem):
        """Provider fetches a single market by ticker and maps it to MarketSnapshot."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/trade-api/v2/markets/KXCPICORE-26JUN-T3.0"
            return httpx.Response(
                200,
                json={
                    "market": {
                        "ticker": "KXCPICORE-26JUN-T3.0",
                        "title": "Will core CPI inflation be above 3.0% in June 2026?",
                        "status": "open",
                        "close_time": "2026-06-10T14:00:00Z",
                        "yes_bid_dollars": "0.4100",
                        "yes_ask_dollars": "0.4400",
                        "no_bid_dollars": "0.5600",
                        "no_ask_dollars": "0.5900",
                        "volume_fp": "4200.00",
                    }
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://external-api.kalshi.com",
        ) as client:
            provider = KalshiMarketDataProvider(
                api_key_id="test_key_id",
                private_key_pem=rsa_private_key_pem,
                http_client=client,
                base_url="https://external-api.kalshi.com",
            )
            snapshot = await provider.get_market_snapshot("KXCPICORE-26JUN-T3.0")

        assert snapshot is not None
        assert snapshot.market_id == "KXCPICORE-26JUN-T3.0"
        assert snapshot.yes_mid == pytest.approx(0.425)

    async def test_kalshi_get_market_snapshot_returns_none_on_404(self, rsa_private_key_pem):
        """Provider returns None for missing markets."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": {"message": "not found"}})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://external-api.kalshi.com",
        ) as client:
            provider = KalshiMarketDataProvider(
                api_key_id="test_key_id",
                private_key_pem=rsa_private_key_pem,
                http_client=client,
                base_url="https://external-api.kalshi.com",
            )
            snapshot = await provider.get_market_snapshot("MISSING")

        assert snapshot is None

    async def test_kalshi_get_orderbook_fetches_raw_orderbook(self, rsa_private_key_pem):
        """Provider exposes raw orderbook for later executable-price validation."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/trade-api/v2/markets/MARKET-1/orderbook"
            return httpx.Response(
                200,
                json={
                    "orderbook_fp": {
                        "yes_dollars": [["0.4100", "100.00"]],
                        "no_dollars": [["0.5600", "50.00"]],
                    }
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://external-api.kalshi.com",
        ) as client:
            provider = KalshiMarketDataProvider(
                api_key_id="test_key_id",
                private_key_pem=rsa_private_key_pem,
                http_client=client,
                base_url="https://external-api.kalshi.com",
            )
            orderbook = await provider.get_orderbook("MARKET-1")

        assert orderbook["orderbook_fp"]["yes_dollars"] == [["0.4100", "100.00"]]

    async def test_kalshi_historical_snapshots_empty(self, kalshi_provider):
        """Historical snapshots remain disabled until a separate historical adapter is added."""
        result = await kalshi_provider.get_historical_snapshots(
            "WEATHER-24-WV-RAIN-20240624",
            start_time="2024-06-01T00:00:00Z",
            end_time="2024-06-30T23:59:59Z",
        )
        assert result == []
