"""Bayesian decision engine with MixMCP and deterministic risk gates."""

import logging
from datetime import datetime, timezone
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

    def compute_side_edges(
        self, market_snapshot: MarketSnapshot, probability_yes: float
    ) -> dict[str, float]:
        """Compute side-aware edge using executable ask prices.

        YES edge: P(YES) - YES ask
        NO edge: P(NO) - NO ask
        """
        probability_no = 1.0 - probability_yes
        return {
            "YES": probability_yes - market_snapshot.yes_ask,
            "NO": probability_no - market_snapshot.no_ask,
        }

    def choose_trade_side(
        self,
        market_snapshot: MarketSnapshot,
        probability_yes: float,
        min_edge: float,
    ) -> tuple[Optional[str], float, float]:
        """Choose the best positive side based on executable ask-price edge.

        Returns:
            (side, edge, price). side is None when no side meets min_edge.
        """
        side_edges = self.compute_side_edges(market_snapshot, probability_yes)
        edge_cost = (
            self.config.risk_gate.estimated_fee_probability_equivalent
            + self.config.risk_gate.slippage_buffer
        )
        yes_edge = side_edges["YES"] - edge_cost
        no_edge = side_edges["NO"] - edge_cost

        if yes_edge >= no_edge:
            best_side: Optional[str] = "YES"
            best_edge = yes_edge
            best_price = market_snapshot.yes_ask
        else:
            best_side = "NO"
            best_edge = no_edge
            best_price = market_snapshot.no_ask

        if best_edge < min_edge:
            return None, best_edge, best_price
        return best_side, best_edge, best_price

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

    def _parse_iso_datetime(self, value: str) -> datetime:
        """Parse ISO8601 timestamps, accepting trailing Z as UTC."""
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def check_market_quality(
        self, market_snapshot: MarketSnapshot, now_iso: Optional[str] = None
    ) -> tuple[bool, Optional[str], dict[str, str]]:
        """Evaluate deterministic pre-research market quality gates."""
        gates: dict[str, str] = {}
        first_failed_reason: Optional[str] = None

        def record(gate: str, passed: bool, reason: str) -> None:
            nonlocal first_failed_reason
            gates[gate] = "PASS" if passed else "FAIL"
            if not passed and first_failed_reason is None:
                first_failed_reason = reason

        record("market_open", market_snapshot.status.lower() == "open", "market_not_open")

        quotes_present = (
            market_snapshot.yes_bid > 0
            and market_snapshot.yes_ask > 0
            and market_snapshot.no_bid > 0
            and market_snapshot.no_ask > 0
            and market_snapshot.yes_ask >= market_snapshot.yes_bid
            and market_snapshot.no_ask >= market_snapshot.no_bid
        )
        record("quotes_present", quotes_present, "quotes_missing")

        max_spread = self.config.risk_gate.max_market_spread
        spread_ok = (
            (market_snapshot.yes_ask - market_snapshot.yes_bid) <= max_spread
            and (market_snapshot.no_ask - market_snapshot.no_bid) <= max_spread
        )
        record("spread_acceptable", spread_ok, "spread_too_wide")

        volume_ok = market_snapshot.volume >= self.config.risk_gate.min_market_volume
        record("volume_acceptable", volume_ok, "volume_too_low")

        liquidity_ok = (
            market_snapshot.liquidity is None
            or market_snapshot.liquidity >= self.config.risk_gate.min_market_liquidity
        )
        record("liquidity_acceptable", liquidity_ok, "liquidity_too_low")

        close_time_ok = True
        if market_snapshot.close_time:
            now = self._parse_iso_datetime(now_iso) if now_iso else datetime.now(timezone.utc)
            close_time = self._parse_iso_datetime(market_snapshot.close_time)
            hours_to_close = (close_time - now).total_seconds() / 3600.0
            close_time_ok = hours_to_close >= self.config.risk_gate.min_hours_to_close
        record("close_time_acceptable", close_time_ok, "close_time_too_soon")

        return first_failed_reason is None, first_failed_reason, gates

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

    def evaluate_paper_decision(
        self,
        market_snapshot: MarketSnapshot,
        probability_yes: float,
        category: str,
        research_usable: bool,
        source_fresh: bool,
        llm_parse_ok: bool,
        confidence_ok: bool,
        signal_count: int,
        signals_conflict: bool,
        sizing_contracts: int,
        enabled_for_paper: bool = True,
        daily_trade_count_ok: bool = True,
        daily_exposure_ok: bool = True,
        category_exposure_ok: bool = True,
        series_exposure_ok: bool = True,
        min_edge: float = 0.05,
    ) -> Decision:
        """Evaluate paper trading gates in deterministic audit order."""
        trace_id = get_trace_id()
        gates: dict[str, str] = {}
        first_failed_reason: Optional[str] = None

        def record(gate: str, passed: bool, reason: str) -> None:
            nonlocal first_failed_reason
            gates[gate] = "PASS" if passed else "FAIL"
            if not passed and first_failed_reason is None:
                first_failed_reason = reason

        record("market_open", market_snapshot.status.lower() == "open", "market_not_open")

        quotes_present = (
            market_snapshot.yes_bid > 0
            and market_snapshot.yes_ask > 0
            and market_snapshot.no_bid > 0
            and market_snapshot.no_ask > 0
            and market_snapshot.yes_ask >= market_snapshot.yes_bid
            and market_snapshot.no_ask >= market_snapshot.no_bid
        )
        record("quotes_present", quotes_present, "quotes_missing")

        max_spread = self.config.risk_gate.max_market_spread
        spread_ok = (
            (market_snapshot.yes_ask - market_snapshot.yes_bid) <= max_spread
            and (market_snapshot.no_ask - market_snapshot.no_bid) <= max_spread
        )
        record("spread_acceptable", spread_ok, "spread_too_wide")

        liquidity_ok = (
            market_snapshot.liquidity is None
            or market_snapshot.liquidity >= self.config.risk_gate.min_market_liquidity
        )
        record("liquidity_acceptable", liquidity_ok, "liquidity_too_low")

        category_supported = category in {"economics", "weather", "sports", "politics"}
        record("category_supported", category_supported, "category_unsupported")
        record(
            "category_enabled_for_paper",
            enabled_for_paper,
            "category_disabled_for_paper",
        )
        record("research_usable", research_usable, "research_unusable")
        record("source_freshness_acceptable", source_fresh, "source_stale")
        record("llm_parse_ok", llm_parse_ok, "llm_parse_failed")
        record("confidence_acceptable", confidence_ok, "confidence_too_low")
        record("signal_count_acceptable", signal_count > 0, "insufficient_signals")
        record("confluence_acceptable", not signals_conflict, "signals_conflict")

        side, edge, market_price = self.choose_trade_side(
            market_snapshot=market_snapshot,
            probability_yes=probability_yes,
            min_edge=min_edge,
        )
        record("net_edge_acceptable", side is not None, "net_edge_below_threshold")
        record("sizing_above_minimum", sizing_contracts > 0, "sizing_below_minimum")
        record(
            "daily_trade_count_acceptable",
            daily_trade_count_ok,
            "daily_trade_limit_reached",
        )
        record("daily_exposure_acceptable", daily_exposure_ok, "daily_exposure_limit_reached")
        record(
            "category_exposure_acceptable",
            category_exposure_ok,
            "category_exposure_limit_reached",
        )
        record(
            "series_exposure_acceptable",
            series_exposure_ok,
            "series_exposure_limit_reached",
        )

        if first_failed_reason is not None:
            return Decision(
                decision_id=trace_id,
                market_id=market_snapshot.market_id,
                mixed_probability=probability_yes,
                market_implied_probability=market_price,
                edge=edge,
                expected_value=edge * 100,
                risk_gate_result="FAIL",
                decision="NO_TRADE",
                trace_id=trace_id,
                category=category,
                skip_reason=first_failed_reason,
                gate_results=gates,
            )

        return Decision(
            decision_id=trace_id,
            market_id=market_snapshot.market_id,
            mixed_probability=probability_yes,
            market_implied_probability=market_price,
            edge=edge,
            expected_value=edge * 100,
            risk_gate_result="PASS",
            decision=f"BUY_{side}",
            trace_id=trace_id,
            category=category,
            skip_reason=None,
            gate_results=gates,
        )

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

        side, edge, market_price = self.choose_trade_side(
            market_snapshot=market_snapshot,
            probability_yes=our_probability,
            min_edge=gap_threshold_pct,
        )

        # Use config default if not specified
        if max_position_usd is None:
            max_position_usd = self.config.execution.max_position_usd

        # Check all gates (fail-closed: ALL must pass)
        confidence_pass = self.check_confidence_gate(probability=our_probability)
        position_pass = self.check_position_size_gate(max_position_usd=max_position_usd)
        daily_loss_pass = self.check_daily_loss_gate(daily_loss_so_far=daily_loss_so_far)

        all_gates_pass = confidence_pass and position_pass and daily_loss_pass
        skip_reason: Optional[str]

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
        elif side is not None:
            decision_str = f"BUY_{side}"
            risk_gate_result = "PASS"
            logger.info(
                f"Trade decision: BUY_{side}",
                extra={
                    "trace_id": trace_id,
                    "market_id": market_snapshot.market_id,
                    "side": side,
                    "edge": edge,
                    "threshold": gap_threshold_pct,
                },
            )
        else:
            # Insufficient edge: no trade (but gates passed)
            decision_str = "NO_TRADE"
            risk_gate_result = "PASS"
            skip_reason = "net_edge_below_threshold"
            logger.debug(
                "No trade: insufficient edge",
                extra={
                    "trace_id": trace_id,
                    "market_id": market_snapshot.market_id,
                    "edge": edge,
                    "threshold": gap_threshold_pct,
                },
            )
            # Store the most favorable net edge even when it is not tradeable.
            side_edges = self.compute_side_edges(market_snapshot, our_probability)
            market_price = (
                market_snapshot.yes_ask
                if side_edges["YES"] >= side_edges["NO"]
                else market_snapshot.no_ask
            )
        if decision_str != "NO_TRADE" or risk_gate_result == "FAIL":
            skip_reason = None

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
            skip_reason=skip_reason,
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
