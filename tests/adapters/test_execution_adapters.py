"""Tests for ExecutionProvider abstract interface and implementations."""

from datetime import datetime, timezone

import pytest

from kal_predict.adapters.execution import (
    ExecutionProvider,
    MockExecutionProvider,
    PaperExecutionProvider,
)
from kal_predict.models import TradeIntent


class TestExecutionProviderInterface:
    """Test abstract interface is properly defined."""

    def test_execution_provider_is_abstract(self):
        """Verify ExecutionProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ExecutionProvider()  # type: ignore


@pytest.mark.asyncio
class TestPaperExecutionProvider:
    """Test PaperExecutionProvider paper trading simulator."""

    @pytest.fixture
    def paper_provider(self):
        """Create a PaperExecutionProvider instance."""
        return PaperExecutionProvider()

    @pytest.fixture
    def sample_trade_intent(self):
        """Create a sample TradeIntent for YES side."""
        now = datetime.now(timezone.utc).isoformat()
        return TradeIntent(
            intent_id="intent-001",
            market_id="WEATHER-24-WV-RAIN-20240624",
            side="YES",
            max_price=0.60,
            size=10,
            mode="paper",
            created_at=now,
            trace_id="trace-001",
        )

    async def test_paper_execution_simulator_fills_order(self, paper_provider, sample_trade_intent):
        """Verify paper provider fills order at appropriate price."""
        market_bid = 0.55
        market_ask = 0.65

        # BUY YES should fill at min(max_price, ask) = min(0.60, 0.65) = 0.60
        result = await paper_provider.execute_trade(sample_trade_intent, market_bid, market_ask)

        assert result is not None
        assert result["order_id"] is not None
        assert result["market_id"] == "WEATHER-24-WV-RAIN-20240624"
        assert result["side"] == "YES"
        assert result["fill_price"] == 0.60
        assert result["size"] == 10
        assert result["mode"] == "paper"
        assert "fees" in result
        assert "timestamp" in result

    async def test_paper_execution_rejects_live_mode(self, paper_provider):
        """Verify paper provider rejects live mode trades."""
        now = datetime.now(timezone.utc).isoformat()
        live_intent = TradeIntent(
            intent_id="intent-002",
            market_id="WEATHER-24-WV-RAIN-20240624",
            side="YES",
            max_price=0.60,
            size=10,
            mode="live",  # Live mode should be rejected
            created_at=now,
            trace_id="trace-002",
        )

        result = await paper_provider.execute_trade(live_intent, 0.55, 0.65)

        assert result is None

    async def test_paper_execution_tracks_position(self, paper_provider, sample_trade_intent):
        """Verify paper provider tracks position correctly."""
        # First trade
        result1 = await paper_provider.execute_trade(
            sample_trade_intent, market_bid=0.55, market_ask=0.65
        )

        assert result1 is not None

        # Check position
        position = await paper_provider.get_position("WEATHER-24-WV-RAIN-20240624")

        assert position is not None
        assert position["size"] == 10
        assert position["avg_price"] == 0.60

        # Second trade (buy more)
        now = datetime.now(timezone.utc).isoformat()
        intent2 = TradeIntent(
            intent_id="intent-003",
            market_id="WEATHER-24-WV-RAIN-20240624",
            side="YES",
            max_price=0.70,
            size=5,
            mode="paper",
            created_at=now,
            trace_id="trace-003",
        )

        result2 = await paper_provider.execute_trade(intent2, market_bid=0.60, market_ask=0.70)

        assert result2 is not None
        assert result2["fill_price"] == 0.70

        # Check updated position (weighted average price)
        position = await paper_provider.get_position("WEATHER-24-WV-RAIN-20240624")

        assert position is not None
        assert position["size"] == 15
        # WAP = (10 * 0.60 + 5 * 0.70) / 15 = (6.0 + 3.5) / 15 = 9.5 / 15 ≈ 0.6333
        assert abs(position["avg_price"] - (9.5 / 15)) < 0.0001

    async def test_paper_execution_applies_fees(self, paper_provider, sample_trade_intent):
        """Verify paper provider applies exchange fees correctly."""
        result = await paper_provider.execute_trade(
            sample_trade_intent, market_bid=0.55, market_ask=0.65
        )

        assert result is not None
        # EXCHANGE_FEE = 0.02 per contract
        # Fees = size * EXCHANGE_FEE = 10 * 0.02 = 0.20
        assert result["fees"] == 0.20

    async def test_paper_execution_respects_max_price_yes(self, paper_provider):
        """Verify paper provider respects max price for YES orders."""
        now = datetime.now(timezone.utc).isoformat()
        intent = TradeIntent(
            intent_id="intent-004",
            market_id="WEATHER-24-WV-RAIN-20240624",
            side="YES",
            max_price=0.50,  # Max price is 0.50
            size=10,
            mode="paper",
            created_at=now,
            trace_id="trace-004",
        )

        # Market ask is 0.65, which is above max_price
        result = await paper_provider.execute_trade(intent, market_bid=0.55, market_ask=0.65)

        assert result is not None
        # Should fill at max_price (0.50) instead of ask (0.65)
        assert result["fill_price"] == 0.50

    async def test_paper_execution_respects_max_price_no(self, paper_provider):
        """Verify paper provider respects max price for NO orders."""
        now = datetime.now(timezone.utc).isoformat()
        intent = TradeIntent(
            intent_id="intent-005",
            market_id="WEATHER-24-WV-RAIN-20240624",
            side="NO",
            max_price=0.30,  # Max price for NO
            size=10,
            mode="paper",
            created_at=now,
            trace_id="trace-005",
        )

        # Market bid is 0.55, which is above max_price
        result = await paper_provider.execute_trade(intent, market_bid=0.55, market_ask=0.65)

        assert result is not None
        # For NO, should fill at max(max_price, bid) = max(0.30, 0.55) = 0.55
        # But if bid > max_price, we reject. Actually, for NO we want to sell,
        # so we want best bid below our limit. If bid > max_price, we can't fill.
        # Let's reconsider: for NO, max_price is the max we want to SELL at,
        # so we want to get the bid, which should be <= max_price
        # If bid > max_price, we should fill at max_price instead
        assert result["fill_price"] == 0.30

    async def test_paper_execution_cancel_order(self, paper_provider):
        """Verify cancel_order succeeds (no-op in paper mode)."""
        result = await paper_provider.cancel_order("some-order-id")

        assert result is True

    async def test_paper_execution_get_position_not_found(self, paper_provider):
        """Verify get_position returns None for unknown market."""
        position = await paper_provider.get_position("UNKNOWN-MARKET-ID")

        assert position is None


@pytest.mark.asyncio
class TestMockExecutionProvider:
    """Test MockExecutionProvider always fills at midpoint."""

    @pytest.fixture
    def mock_provider(self):
        """Create a MockExecutionProvider instance."""
        return MockExecutionProvider()

    @pytest.fixture
    def sample_trade_intent(self):
        """Create a sample TradeIntent."""
        now = datetime.now(timezone.utc).isoformat()
        return TradeIntent(
            intent_id="intent-006",
            market_id="WEATHER-24-WV-RAIN-20240624",
            side="YES",
            max_price=0.60,
            size=10,
            mode="paper",
            created_at=now,
            trace_id="trace-006",
        )

    async def test_mock_execution_always_fills_at_midpoint(
        self, mock_provider, sample_trade_intent
    ):
        """Verify mock provider always fills at midpoint."""
        market_bid = 0.50
        market_ask = 0.70

        result = await mock_provider.execute_trade(sample_trade_intent, market_bid, market_ask)

        assert result is not None
        # Midpoint = (0.50 + 0.70) / 2 = 0.60
        assert result["fill_price"] == 0.60
        assert result["side"] == "YES"
        assert result["size"] == 10

    async def test_mock_execution_no_fees(self, mock_provider, sample_trade_intent):
        """Verify mock provider has no fees."""
        result = await mock_provider.execute_trade(
            sample_trade_intent, market_bid=0.50, market_ask=0.70
        )

        assert result is not None
        assert result["fees"] == 0

    async def test_mock_execution_get_position_returns_zero(self, mock_provider):
        """Verify mock provider returns zero position (stateless)."""
        position = await mock_provider.get_position("ANY-MARKET-ID")

        assert position is not None
        assert position["size"] == 0
        assert position["avg_price"] == 0
        assert position["pnl"] == 0

    async def test_mock_execution_cancel_order(self, mock_provider):
        """Verify cancel_order succeeds for mock provider."""
        result = await mock_provider.cancel_order("some-order-id")

        assert result is True
