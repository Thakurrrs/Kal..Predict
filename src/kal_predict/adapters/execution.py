"""Abstract and concrete execution provider implementations."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from kal_predict.config import ExecutionConfig
from kal_predict.logging_setup import get_logger
from kal_predict.models import TradeIntent

logger = get_logger(__name__)

# Exchange fee per contract (in dollars)
EXCHANGE_FEE = 0.02


class ExecutionProvider(ABC):
    """Abstract base class for execution providers."""

    @abstractmethod
    async def execute_trade(
        self, intent: TradeIntent, market_bid: float, market_ask: float
    ) -> Optional[dict[str, Any]]:
        """Execute a trade intent (if risk gates passed).

        Args:
            intent: TradeIntent with side, max_price, size, mode
            market_bid: Current best bid price for the market
            market_ask: Current best ask price for the market

        Returns:
            Fill dict with order_id, market_id, side, fill_price, size, fees, timestamp, mode
            if successful, None otherwise (e.g., mode=live, rejected)
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.

        Args:
            order_id: The order ID to cancel

        Returns:
            True if cancelled (or no-op in paper mode), False otherwise
        """
        pass

    @abstractmethod
    async def get_position(self, market_id: str) -> Optional[dict[str, Any]]:
        """Get current position in a market.

        Args:
            market_id: The Kalshi market ID

        Returns:
            Position dict with size, avg_price, pnl if position exists, None otherwise
        """
        pass


class PaperExecutionProvider(ExecutionProvider):
    """Paper trading simulator.

    Fills orders at best available prices respecting max_price limits,
    applies realistic fees, and tracks position with weighted average pricing.
    Rejects live mode trades (fail-closed constraint).
    """

    def __init__(self, execution_config: Optional[ExecutionConfig] = None) -> None:
        """Initialize paper execution provider."""
        self._execution_config = execution_config or ExecutionConfig()
        # positions: market_id -> {size, avg_price, pnl}
        self._positions: dict[str, dict[str, float]] = {}
        # trades: list of all fills with full details
        self._trades: list[dict[str, Any]] = []

        logger.info(
            "PaperExecutionProvider initialized",
            extra={
                "event_type": "provider_init",
                "actor": "paper_execution_provider",
            },
        )

    async def execute_trade(
        self, intent: TradeIntent, market_bid: float, market_ask: float
    ) -> Optional[dict[str, Any]]:
        """Execute a trade in paper mode.

        Args:
            intent: TradeIntent with side, max_price, size, mode
            market_bid: Current best bid price
            market_ask: Current best ask price

        Returns:
            Fill dict if successful and mode=paper, None if mode=live or cannot fill
        """
        # Fail-closed: reject live mode unless explicitly enabled. Even when enabled,
        # this paper provider does not submit live orders.
        if intent.mode == "live":
            live_allowed = (
                self._execution_config.mode == "live"
                and self._execution_config.live_trading_enabled
            )
            logger.error(
                "Trade execution blocked: live mode not available in paper provider",
                extra={
                    "event_type": "execution_blocked",
                    "actor": "paper_execution_provider",
                    "reason": (
                        "paper_provider_live_not_supported"
                        if live_allowed
                        else "live_mode_disabled"
                    ),
                    "mode": intent.mode,
                    "trace_id": intent.trace_id,
                },
            )
            return None
        if intent.mode != "paper":
            logger.error(
                "Trade execution blocked: unsupported execution mode",
                extra={
                    "event_type": "execution_blocked",
                    "actor": "paper_execution_provider",
                    "reason": "unsupported_mode",
                    "mode": intent.mode,
                    "trace_id": intent.trace_id,
                },
            )
            return None

        # Determine fill price based on side
        if intent.side == "YES":
            # Buying YES: fill at min(max_price, ask)
            fill_price = min(intent.max_price, market_ask)
        elif intent.side == "NO":
            # Selling NO (buying protection): fill at min(max_price, bid)
            # But if bid > max_price, we want to sell at max_price
            fill_price = min(intent.max_price, market_bid)
        else:
            logger.error(
                "Invalid trade side",
                extra={
                    "event_type": "execution_error",
                    "actor": "paper_execution_provider",
                    "side": intent.side,
                    "trace_id": intent.trace_id,
                },
            )
            return None

        # Calculate fees
        fees = intent.size * EXCHANGE_FEE

        # Create order
        order_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Update position
        position = self._positions.get(intent.market_id)
        if position is None:
            position = {"size": 0, "avg_price": 0.0, "pnl": 0.0}
            self._positions[intent.market_id] = position

        # Update weighted average price
        old_size = position["size"]
        old_avg_price = position["avg_price"]
        new_size = old_size + intent.size
        if new_size > 0:
            # Weighted average: (old_size * old_avg_price + new_size * fill_price) / new_size
            new_avg_price = (old_size * old_avg_price + intent.size * fill_price) / new_size
        else:
            new_avg_price = fill_price

        position["size"] = new_size
        position["avg_price"] = new_avg_price

        # Create fill record
        fill = {
            "order_id": order_id,
            "market_id": intent.market_id,
            "side": intent.side,
            "fill_price": fill_price,
            "size": intent.size,
            "fees": fees,
            "timestamp": timestamp,
            "mode": "paper",
        }

        self._trades.append(fill)

        logger.info(
            "Paper trade executed",
            extra={
                "event_type": "fill",
                "actor": "paper_execution_provider",
                "order_id": order_id,
                "market_id": intent.market_id,
                "side": intent.side,
                "fill_price": fill_price,
                "size": intent.size,
                "fees": fees,
                "trace_id": intent.trace_id,
            },
        )

        return fill

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order (no-op in paper mode).

        Args:
            order_id: The order ID to cancel

        Returns:
            True (always succeeds in paper mode)
        """
        logger.info(
            "Order cancellation requested (paper mode no-op)",
            extra={
                "event_type": "cancel_order",
                "actor": "paper_execution_provider",
                "order_id": order_id,
            },
        )
        return True

    async def get_position(self, market_id: str) -> Optional[dict[str, Any]]:
        """Get position in a market.

        Args:
            market_id: The market ID

        Returns:
            Position dict {size, avg_price, pnl} or None if no position
        """
        return self._positions.get(market_id)


class MockExecutionProvider(ExecutionProvider):
    """Mock execution provider for unit tests.

    Always fills at midpoint with no fees.
    Stateless (no position tracking).
    """

    def __init__(self) -> None:
        """Initialize mock execution provider."""
        logger.info(
            "MockExecutionProvider initialized",
            extra={
                "event_type": "provider_init",
                "actor": "mock_execution_provider",
            },
        )

    async def execute_trade(
        self, intent: TradeIntent, market_bid: float, market_ask: float
    ) -> Optional[dict[str, Any]]:
        """Execute a trade at midpoint with no fees.

        Args:
            intent: TradeIntent with side, size
            market_bid: Current best bid price
            market_ask: Current best ask price

        Returns:
            Fill dict with midpoint fill price and zero fees
        """
        # Fill at midpoint
        fill_price = (market_bid + market_ask) / 2

        order_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        fill = {
            "order_id": order_id,
            "market_id": intent.market_id,
            "side": intent.side,
            "fill_price": fill_price,
            "size": intent.size,
            "fees": 0,
            "timestamp": timestamp,
            "mode": "mock",
        }

        logger.info(
            "Mock trade executed",
            extra={
                "event_type": "fill",
                "actor": "mock_execution_provider",
                "order_id": order_id,
                "market_id": intent.market_id,
                "side": intent.side,
                "fill_price": fill_price,
                "size": intent.size,
                "trace_id": intent.trace_id,
            },
        )

        return fill

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order (no-op for mock provider).

        Args:
            order_id: The order ID to cancel

        Returns:
            True (always succeeds)
        """
        logger.info(
            "Order cancellation requested (mock mode no-op)",
            extra={
                "event_type": "cancel_order",
                "actor": "mock_execution_provider",
                "order_id": order_id,
            },
        )
        return True

    async def get_position(self, market_id: str) -> Optional[dict[str, Any]]:
        """Get position (always returns zero for mock, stateless).

        Args:
            market_id: The market ID

        Returns:
            Zero position dict (mock provider is stateless)
        """
        return {"size": 0, "avg_price": 0.0, "pnl": 0.0}
