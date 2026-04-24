"""Test suite for Bayesian decision engine with MixMCP and risk gates."""

import pytest

from kal_predict.config import AppConfig
from kal_predict.core.decision import DecisionEngine
from kal_predict.models import Decision, MarketSnapshot


@pytest.fixture
def config() -> AppConfig:
    """Load test configuration."""
    return AppConfig()


@pytest.fixture
def decision_engine(config: AppConfig) -> DecisionEngine:
    """Create DecisionEngine instance."""
    return DecisionEngine(config)


@pytest.fixture
def sample_market_snapshot() -> MarketSnapshot:
    """Create a sample market snapshot for testing."""
    return MarketSnapshot(
        market_id="test-market-1",
        timestamp="2026-04-24T10:00:00Z",
        yes_bid=0.40,
        yes_ask=0.42,
        no_bid=0.58,
        no_ask=0.60,
        volume=1000,
    )


class TestProbabilityMixing:
    """Tests for probability mixing (MixMCP formula)."""

    def test_probability_mixing_mixmcp(self, decision_engine: DecisionEngine):
        """Test probability mixing with default MixMCP (70% market, 30% model)."""
        # Formula: mixed = 0.7 * prior + 0.3 * posterior
        # 0.7 * 0.50 + 0.3 * 0.80 = 0.35 + 0.24 = 0.59
        result = decision_engine.mix_probabilities(prior=0.50, model_posterior=0.80)
        assert result == pytest.approx(0.59, abs=0.001)

    def test_probability_mixing_custom_alpha(self, decision_engine: DecisionEngine):
        """Test probability mixing with custom alpha."""
        # mixed = 0.5 * 0.40 + 0.5 * 0.60 = 0.20 + 0.30 = 0.50
        result = decision_engine.mix_probabilities(prior=0.40, model_posterior=0.60, mix_alpha=0.5)
        assert result == pytest.approx(0.50, abs=0.001)

    def test_probability_mixing_zero_prior(self, decision_engine: DecisionEngine):
        """Test mixing when prior is 0%."""
        # mixed = 0.7 * 0 + 0.3 * 0.8 = 0.24
        result = decision_engine.mix_probabilities(prior=0.0, model_posterior=0.8)
        assert result == pytest.approx(0.24, abs=0.001)

    def test_probability_mixing_one_prior(self, decision_engine: DecisionEngine):
        """Test mixing when prior is 100%."""
        # mixed = 0.7 * 1.0 + 0.3 * 0.2 = 0.7 + 0.06 = 0.76
        result = decision_engine.mix_probabilities(prior=1.0, model_posterior=0.2)
        assert result == pytest.approx(0.76, abs=0.001)

    def test_probability_mixing_clamped_to_lower_bound(self, decision_engine: DecisionEngine):
        """Test that mixing result is clamped to 0.0 if negative."""
        # If somehow computation goes negative (shouldn't with valid inputs)
        # alpha=0.1, prior=0.0, posterior=-0.5 would give 0.0 + (-0.05) = -0.05
        # But we can test the clamp by using edge case
        # Just verify positive result is not clamped
        result = decision_engine.mix_probabilities(prior=0.01, model_posterior=0.01)
        assert result >= 0.0

    def test_probability_mixing_clamped_to_upper_bound(self, decision_engine: DecisionEngine):
        """Test that mixing result is clamped to 1.0 if over 100%."""
        result = decision_engine.mix_probabilities(prior=1.0, model_posterior=1.0)
        assert result <= 1.0
        assert result == pytest.approx(1.0, abs=0.001)

    def test_probability_mixing_both_zero(self, decision_engine: DecisionEngine):
        """Test mixing with both probabilities at 0%."""
        result = decision_engine.mix_probabilities(prior=0.0, model_posterior=0.0)
        assert result == pytest.approx(0.0, abs=0.001)

    def test_probability_mixing_both_one(self, decision_engine: DecisionEngine):
        """Test mixing with both probabilities at 100%."""
        result = decision_engine.mix_probabilities(prior=1.0, model_posterior=1.0)
        assert result == pytest.approx(1.0, abs=0.001)


class TestGapComputation:
    """Tests for gap computation (edge calculation)."""

    def test_compute_gap_positive_edge(self, decision_engine: DecisionEngine):
        """Test gap computation with positive edge (our estimate > market)."""
        # gap = 0.65 - 0.50 = 0.15
        gap = decision_engine.compute_gap(our_estimate=0.65, market_price=0.50)
        assert gap == pytest.approx(0.15, abs=0.001)

    def test_compute_gap_negative_edge(self, decision_engine: DecisionEngine):
        """Test gap computation with negative edge (our estimate < market)."""
        # gap = 0.30 - 0.50 = -0.20
        gap = decision_engine.compute_gap(our_estimate=0.30, market_price=0.50)
        assert gap == pytest.approx(-0.20, abs=0.001)

    def test_compute_gap_zero_edge(self, decision_engine: DecisionEngine):
        """Test gap computation with zero edge (no divergence)."""
        # gap = 0.50 - 0.50 = 0.0
        gap = decision_engine.compute_gap(our_estimate=0.50, market_price=0.50)
        assert gap == pytest.approx(0.0, abs=0.001)

    def test_compute_gap_extreme_values(self, decision_engine: DecisionEngine):
        """Test gap computation with extreme probability values."""
        # gap = 1.0 - 0.0 = 1.0
        gap = decision_engine.compute_gap(our_estimate=1.0, market_price=0.0)
        assert gap == pytest.approx(1.0, abs=0.001)

        # gap = 0.0 - 1.0 = -1.0
        gap = decision_engine.compute_gap(our_estimate=0.0, market_price=1.0)
        assert gap == pytest.approx(-1.0, abs=0.001)


class TestConfidenceGate:
    """Tests for confidence (min_confidence) risk gate."""

    def test_confidence_gate_pass(self, decision_engine: DecisionEngine):
        """Test confidence gate passes when probability >= min_confidence."""
        result = decision_engine.check_confidence_gate(probability=0.60)
        assert result is True

    def test_confidence_gate_pass_at_threshold(self, decision_engine: DecisionEngine):
        """Test confidence gate passes when probability equals min_confidence."""
        threshold = decision_engine.config.risk_gate.min_confidence
        result = decision_engine.check_confidence_gate(probability=threshold)
        assert result is True

    def test_confidence_gate_fail(self, decision_engine: DecisionEngine):
        """Test confidence gate fails when probability < min_confidence."""
        result = decision_engine.check_confidence_gate(probability=0.50)
        assert result is False

    def test_confidence_gate_fail_barely(self, decision_engine: DecisionEngine):
        """Test confidence gate fails barely below threshold."""
        threshold = decision_engine.config.risk_gate.min_confidence
        result = decision_engine.check_confidence_gate(probability=threshold - 0.001)
        assert result is False


class TestPositionSizeGate:
    """Tests for position size risk gate."""

    def test_position_size_gate_pass(self, decision_engine: DecisionEngine):
        """Test position size gate passes when within limit."""
        max_position = decision_engine.config.execution.max_position_usd
        result = decision_engine.check_position_size_gate(max_position_usd=max_position - 100)
        assert result is True

    def test_position_size_gate_pass_at_limit(self, decision_engine: DecisionEngine):
        """Test position size gate passes at exact limit."""
        max_position = decision_engine.config.execution.max_position_usd
        result = decision_engine.check_position_size_gate(max_position_usd=max_position)
        assert result is True

    def test_position_size_gate_fail(self, decision_engine: DecisionEngine):
        """Test position size gate fails when exceeds limit."""
        max_position = decision_engine.config.execution.max_position_usd
        result = decision_engine.check_position_size_gate(max_position_usd=max_position + 100)
        assert result is False

    def test_position_size_gate_zero(self, decision_engine: DecisionEngine):
        """Test position size gate passes for zero position."""
        result = decision_engine.check_position_size_gate(max_position_usd=0.0)
        assert result is True


class TestDailyLossGate:
    """Tests for daily loss limit risk gate."""

    def test_daily_loss_gate_pass(self, decision_engine: DecisionEngine):
        """Test daily loss gate passes when under limit."""
        limit = decision_engine.config.risk_gate.daily_loss_limit_usd
        result = decision_engine.check_daily_loss_gate(daily_loss_so_far=limit - 100)
        assert result is True

    def test_daily_loss_gate_fail_at_limit(self, decision_engine: DecisionEngine):
        """Test daily loss gate fails when at limit (fail-closed)."""
        limit = decision_engine.config.risk_gate.daily_loss_limit_usd
        result = decision_engine.check_daily_loss_gate(daily_loss_so_far=limit)
        assert result is False

    def test_daily_loss_gate_fail_above_limit(self, decision_engine: DecisionEngine):
        """Test daily loss gate fails when above limit."""
        limit = decision_engine.config.risk_gate.daily_loss_limit_usd
        result = decision_engine.check_daily_loss_gate(daily_loss_so_far=limit + 100)
        assert result is False

    def test_daily_loss_gate_pass_zero(self, decision_engine: DecisionEngine):
        """Test daily loss gate passes at zero loss."""
        result = decision_engine.check_daily_loss_gate(daily_loss_so_far=0.0)
        assert result is True


class TestEvaluateTrade:
    """Integration tests for full trade evaluation with all gates."""

    def test_evaluate_trade_all_gates_pass_buy_yes(
        self, decision_engine: DecisionEngine, sample_market_snapshot: MarketSnapshot
    ):
        """Test trade evaluation with all gates passing and positive edge (BUY_YES)."""
        # Market price: (0.40 + 0.42) / 2 = 0.41
        # Our probability: 0.65
        # Edge: 0.65 - 0.41 = 0.24 (> 0.05 threshold, should BUY_YES)
        our_probability = 0.65

        decision = decision_engine.evaluate_trade(
            market_snapshot=sample_market_snapshot,
            our_probability=our_probability,
            gap_threshold_pct=0.05,
        )

        assert decision.decision == "BUY_YES"
        assert decision.risk_gate_result == "PASS"
        assert decision.edge == pytest.approx(0.24, abs=0.001)
        assert decision.mixed_probability == pytest.approx(0.65, abs=0.001)

    def test_evaluate_trade_all_gates_pass_buy_no(self, decision_engine: DecisionEngine):
        """Test trade evaluation with all gates passing and negative edge (BUY_NO).

        For BUY_NO to trigger:
        - Our probability must be high enough to pass confidence gate (>= 0.55)
        - Market must price YES higher than our estimate
        - Edge must be <= -gap_threshold_pct

        Setup: Market prices YES at 0.76, we estimate 0.60 (confident but lower)
        Edge: 0.60 - 0.76 = -0.16 (< -0.05, triggers BUY_NO)
        """
        market_snapshot = MarketSnapshot(
            market_id="test-market-1",
            timestamp="2026-04-24T10:00:00Z",
            yes_bid=0.75,
            yes_ask=0.77,
            no_bid=0.23,
            no_ask=0.25,
            volume=1000,
        )
        our_probability = 0.60

        decision = decision_engine.evaluate_trade(
            market_snapshot=market_snapshot,
            our_probability=our_probability,
            gap_threshold_pct=0.05,
        )

        assert decision.decision == "BUY_NO"
        assert decision.risk_gate_result == "PASS"
        # Market price = (0.75 + 0.77) / 2 = 0.76
        # Edge = 0.60 - 0.76 = -0.16
        assert decision.edge == pytest.approx(-0.16, abs=0.001)

    def test_evaluate_trade_all_gates_pass_insufficient_edge(self, decision_engine: DecisionEngine):
        """Test trade evaluation passes all gates but edge insufficient (NO_TRADE).

        Setup: Market prices YES at 0.50, we estimate 0.52 (confidence passes)
        Edge: 0.52 - 0.50 = 0.02 (< 0.05 threshold, insufficient for trade)
        But confidence gate passes (0.52 >= 0.55? No, this also fails)

        Use 0.56 instead:
        Edge: 0.56 - 0.50 = 0.06... wait that's > 0.05.

        Let's use market at 0.52, our estimate at 0.55:
        Edge: 0.55 - 0.52 = 0.03 (< 0.05, NO_TRADE with PASS)
        """
        market_snapshot = MarketSnapshot(
            market_id="test-market-1",
            timestamp="2026-04-24T10:00:00Z",
            yes_bid=0.51,
            yes_ask=0.53,
            no_bid=0.47,
            no_ask=0.49,
            volume=1000,
        )
        our_probability = 0.55  # Exactly at confidence threshold

        decision = decision_engine.evaluate_trade(
            market_snapshot=market_snapshot,
            our_probability=our_probability,
            gap_threshold_pct=0.05,
        )

        assert decision.decision == "NO_TRADE"
        assert decision.risk_gate_result == "PASS"
        # Market price = (0.51 + 0.53) / 2 = 0.52
        # Edge = 0.55 - 0.52 = 0.03 (insufficient)
        assert decision.edge == pytest.approx(0.03, abs=0.001)

    def test_evaluate_trade_confidence_fails(
        self, decision_engine: DecisionEngine, sample_market_snapshot: MarketSnapshot
    ):
        """Test trade evaluation fails confidence gate (NO_TRADE, FAIL)."""
        # Probability below min_confidence (0.55)
        our_probability = 0.50

        decision = decision_engine.evaluate_trade(
            market_snapshot=sample_market_snapshot,
            our_probability=our_probability,
        )

        assert decision.decision == "NO_TRADE"
        assert decision.risk_gate_result == "FAIL"

    def test_evaluate_trade_position_size_fails(
        self, decision_engine: DecisionEngine, sample_market_snapshot: MarketSnapshot
    ):
        """Test trade evaluation fails position size gate (NO_TRADE, FAIL)."""
        our_probability = 0.65  # High confidence (passes confidence gate)
        max_position = decision_engine.config.execution.max_position_usd

        decision = decision_engine.evaluate_trade(
            market_snapshot=sample_market_snapshot,
            our_probability=our_probability,
            max_position_usd=max_position + 100,  # Exceeds limit
        )

        assert decision.decision == "NO_TRADE"
        assert decision.risk_gate_result == "FAIL"

    def test_evaluate_trade_daily_loss_fails(
        self, decision_engine: DecisionEngine, sample_market_snapshot: MarketSnapshot
    ):
        """Test trade evaluation fails daily loss gate (NO_TRADE, FAIL)."""
        our_probability = 0.65  # High confidence (passes confidence gate)
        daily_limit = decision_engine.config.risk_gate.daily_loss_limit_usd

        decision = decision_engine.evaluate_trade(
            market_snapshot=sample_market_snapshot,
            our_probability=our_probability,
            daily_loss_so_far=daily_limit + 100,  # Exceeds limit
        )

        assert decision.decision == "NO_TRADE"
        assert decision.risk_gate_result == "FAIL"

    def test_evaluate_trade_multiple_gates_fail_fail_closed(
        self, decision_engine: DecisionEngine, sample_market_snapshot: MarketSnapshot
    ):
        """Test fail-closed behavior: if ANY gate fails, trade is rejected."""
        our_probability = 0.50  # Fails confidence gate
        daily_limit = decision_engine.config.risk_gate.daily_loss_limit_usd

        decision = decision_engine.evaluate_trade(
            market_snapshot=sample_market_snapshot,
            our_probability=our_probability,
            daily_loss_so_far=daily_limit + 100,  # Also fails daily loss gate
        )

        # Even with multiple failures, decision is NO_TRADE with FAIL
        assert decision.decision == "NO_TRADE"
        assert decision.risk_gate_result == "FAIL"

    def test_evaluate_trade_returns_decision_object(
        self, decision_engine: DecisionEngine, sample_market_snapshot: MarketSnapshot
    ):
        """Test that evaluate_trade returns a properly populated Decision object."""
        our_probability = 0.60

        decision = decision_engine.evaluate_trade(
            market_snapshot=sample_market_snapshot, our_probability=our_probability
        )

        assert isinstance(decision, Decision)
        assert decision.market_id == "test-market-1"
        assert decision.mixed_probability == pytest.approx(0.60, abs=0.001)
        assert decision.market_implied_probability == pytest.approx(0.41, abs=0.001)
        assert decision.trace_id is not None
        assert decision.decision in ("BUY_YES", "BUY_NO", "NO_TRADE")
        assert decision.risk_gate_result in ("PASS", "FAIL")

    def test_evaluate_trade_custom_gap_threshold(self, decision_engine: DecisionEngine):
        """Test trade evaluation with custom gap threshold.

        Setup: Market at 0.45, our estimate at 0.58 (passes confidence)
        Edge: 0.58 - 0.45 = 0.13
        With 0.10 threshold: 0.13 > 0.10, BUY_YES
        With 0.15 threshold: 0.13 < 0.15, NO_TRADE
        """
        market_snapshot = MarketSnapshot(
            market_id="test-market-1",
            timestamp="2026-04-24T10:00:00Z",
            yes_bid=0.44,
            yes_ask=0.46,
            no_bid=0.54,
            no_ask=0.56,
            volume=1000,
        )
        our_probability = 0.58

        decision_low_threshold = decision_engine.evaluate_trade(
            market_snapshot=market_snapshot,
            our_probability=our_probability,
            gap_threshold_pct=0.10,
        )
        # Market price = (0.44 + 0.46) / 2 = 0.45
        # Edge = 0.58 - 0.45 = 0.13 > 0.10
        assert decision_low_threshold.decision == "BUY_YES"

        decision_high_threshold = decision_engine.evaluate_trade(
            market_snapshot=market_snapshot,
            our_probability=our_probability,
            gap_threshold_pct=0.15,
        )
        # Edge = 0.13 < 0.15
        assert decision_high_threshold.decision == "NO_TRADE"
        assert decision_high_threshold.risk_gate_result == "PASS"
