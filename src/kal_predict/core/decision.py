"""Bayesian decision engine with MixMCP and deterministic risk gates."""

import logging
from typing import Optional

from kal_predict.config import AppConfig
from kal_predict.models import Decision, MarketSnapshot
from kal_predict.trace import get_trace_id

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Decision engine for probability mixing and risk gate evaluation.

    Implements MixMCP (70% market, 30% model) probability mixing and
    fail-closed risk gates for trading decisions.
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize decision engine with configuration.

        Args:
            config: Application configuration containing risk gate thresholds
        """
        self.config = config
        self.min_confidence = config.risk_gate.min_confidence
        self.max_loss_per_trade = config.risk_gate.max_loss_per_trade_usd
        self.daily_loss_limit = config.risk_gate.daily_loss_limit_usd
        logger.debug(
            "DecisionEngine initialized",
            extra={
                "min_confidence": self.min_confidence,
                "daily_loss_limit": self.daily_loss_limit,
            },
        )

    def mix_probabilities(
        self, prior: float, model_posterior: float, mix_alpha: float = 0.7
    ) -> float:
        """Mix market prior with model posterior probability.

        Uses MixMCP formula: mixed = alpha * prior + (1 - alpha) * posterior
        Default: 70% market weight, 30% model weight.

        Args:
            prior: Market-implied probability (from bid/ask spread)
            model_posterior: LLM model's posterior probability estimate
            mix_alpha: Weight for market prior (default: 0.7 for 70% market, 30% model)

        Returns:
            Mixed probability clamped to [0, 1]
        """
        mixed = mix_alpha * prior + (1 - mix_alpha) * model_posterior
        # Clamp to [0, 1]
        clamped = max(0.0, min(1.0, mixed))
        return clamped

    def compute_gap(self, our_estimate: float, market_price: float) -> float:
        """Compute the edge (divergence) between our estimate and market price.

        Edge can be positive (our estimate higher, BUY_YES opportunity) or
        negative (our estimate lower, BUY_NO opportunity). No clamping applied.

        Args:
            our_estimate: Our probability estimate
            market_price: Market-implied probability (mid-price)

        Returns:
            Edge = our_estimate - market_price (can be negative)
        """
        edge = our_estimate - market_price
        return edge

    def check_confidence_gate(self, probability: float) -> bool:
        """Check if probability meets minimum confidence threshold.

        Fail-closed: returns False if probability < min_confidence.

        Args:
            probability: Probability to evaluate

        Returns:
            True if probability >= min_confidence, False otherwise
        """
        passes = probability >= self.min_confidence
        logger.debug(
            "Confidence gate evaluated",
            extra={
                "probability": probability,
                "threshold": self.min_confidence,
                "passes": passes,
            },
        )
        return passes

    def check_position_size_gate(self, max_position_usd: float) -> bool:
        """Check if proposed position size is within limit.

        Fail-closed: returns False if position > max_position_usd from config.

        Args:
            max_position_usd: Proposed position size in USD

        Returns:
            True if position <= config max, False otherwise
        """
        limit = self.config.execution.max_position_usd
        passes = max_position_usd <= limit
        logger.debug(
            "Position size gate evaluated",
            extra={
                "proposed_position_usd": max_position_usd,
                "limit_usd": limit,
                "passes": passes,
            },
        )
        return passes

    def check_daily_loss_gate(self, daily_loss_so_far: float) -> bool:
        """Check if daily losses are within limit.

        Fail-closed: returns False if daily_loss_so_far >= daily_loss_limit.

        Args:
            daily_loss_so_far: Cumulative losses for the day in USD

        Returns:
            True if daily_loss < limit, False if at/above limit
        """
        passes = daily_loss_so_far < self.daily_loss_limit
        logger.debug(
            "Daily loss gate evaluated",
            extra={
                "daily_loss_so_far": daily_loss_so_far,
                "daily_loss_limit": self.daily_loss_limit,
                "passes": passes,
            },
        )
        return passes

    def evaluate_trade(
        self,
        market_snapshot: MarketSnapshot,
        our_probability: float,
        gap_threshold_pct: float = 0.05,
        max_position_usd: Optional[float] = None,
        daily_loss_so_far: float = 0.0,
    ) -> Decision:
        """Evaluate a trading opportunity with all risk gates (fail-closed).

        ALL gates must pass for a trade to be considered. If any gate fails,
        the result is NO_TRADE with risk_gate_result='FAIL'.

        If all gates pass:
        - If edge >= gap_threshold_pct: BUY_YES
        - If edge <= -gap_threshold_pct: BUY_NO
        - Otherwise: NO_TRADE (insufficient edge, but gates passed)

        Args:
            market_snapshot: Current market state with bid/ask quotes
            our_probability: Our probability estimate for YES
            gap_threshold_pct: Minimum edge threshold to trigger trade (default: 0.05)
            max_position_usd: Proposed position size in USD (default: max from config)
            daily_loss_so_far: Cumulative losses for today (default: 0.0)

        Returns:
            Decision object with all fields populated including trade action,
            edge, probability estimates, and risk gate result
        """
        trace_id = get_trace_id()

        # Compute market-implied probability (mid-price of YES)
        market_price = (market_snapshot.yes_bid + market_snapshot.yes_ask) / 2.0

        # Compute edge (divergence)
        edge = self.compute_gap(our_estimate=our_probability, market_price=market_price)

        # Use config default if not specified
        if max_position_usd is None:
            max_position_usd = self.config.execution.max_position_usd

        # Check all gates (fail-closed: ALL must pass)
        confidence_pass = self.check_confidence_gate(probability=our_probability)
        position_pass = self.check_position_size_gate(max_position_usd=max_position_usd)
        daily_loss_pass = self.check_daily_loss_gate(daily_loss_so_far=daily_loss_so_far)

        all_gates_pass = confidence_pass and position_pass and daily_loss_pass

        # Determine trade decision
        if not all_gates_pass:
            # Risk gate failed: no trade
            decision_str = "NO_TRADE"
            risk_gate_result = "FAIL"
            logger.info(
                "Trade rejected: risk gate failed",
                extra={
                    "trace_id": trace_id,
                    "market_id": market_snapshot.market_id,
                    "confidence_pass": confidence_pass,
                    "position_pass": position_pass,
                    "daily_loss_pass": daily_loss_pass,
                    "edge": edge,
                },
            )
        elif edge >= gap_threshold_pct:
            # Positive edge: consider BUY_YES
            decision_str = "BUY_YES"
            risk_gate_result = "PASS"
            logger.info(
                "Trade decision: BUY_YES",
                extra={
                    "trace_id": trace_id,
                    "market_id": market_snapshot.market_id,
                    "edge": edge,
                    "threshold": gap_threshold_pct,
                },
            )
        elif edge <= -gap_threshold_pct:
            # Negative edge: consider BUY_NO
            decision_str = "BUY_NO"
            risk_gate_result = "PASS"
            logger.info(
                "Trade decision: BUY_NO",
                extra={
                    "trace_id": trace_id,
                    "market_id": market_snapshot.market_id,
                    "edge": edge,
                    "threshold": -gap_threshold_pct,
                },
            )
        else:
            # Insufficient edge: no trade (but gates passed)
            decision_str = "NO_TRADE"
            risk_gate_result = "PASS"
            logger.debug(
                "No trade: insufficient edge",
                extra={
                    "trace_id": trace_id,
                    "market_id": market_snapshot.market_id,
                    "edge": edge,
                    "threshold": gap_threshold_pct,
                },
            )

        # Compute expected value (simplified: edge * contract_value)
        # Assuming $1 per contract (standard in prediction markets)
        expected_value = edge * 100  # Rough approximation for typical position

        # Create decision object
        decision = Decision(
            decision_id=trace_id,
            market_id=market_snapshot.market_id,
            mixed_probability=our_probability,
            market_implied_probability=market_price,
            edge=edge,
            expected_value=expected_value,
            risk_gate_result=risk_gate_result,
            decision=decision_str,
            trace_id=trace_id,
        )

        logger.debug(
            "Trade evaluated",
            extra={
                "trace_id": trace_id,
                "decision": decision_str,
                "risk_gate_result": risk_gate_result,
                "our_probability": our_probability,
                "market_price": market_price,
                "edge": edge,
            },
        )

        return decision
