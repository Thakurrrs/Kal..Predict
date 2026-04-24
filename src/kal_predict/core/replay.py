"""Deterministic replay harness for backtesting with Brier score and calibration metrics."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from kal_predict.adapters.market import MarketDataProvider
from kal_predict.config import AppConfig
from kal_predict.core.decision import DecisionEngine
from kal_predict.logging_setup import get_logger
from kal_predict.services.inference import InferenceService
from kal_predict.trace import get_trace_id

logger = get_logger(__name__)


class BrierScoreCalculator:
    """Calculate Brier score and calibration metrics for probability forecasts.

    Brier score formula: BS = mean((forecast_i - outcome_i)^2)
    - Range: [0, 1] (0 = perfect, 0.25 = random, 1 = worst)
    - Lower is better
    """

    def calculate(self, forecasts_and_outcomes: List[Tuple[float, int]]) -> float:
        """Calculate Brier score from forecast-outcome pairs.

        Args:
            forecasts_and_outcomes: List of (forecast_probability, actual_outcome)
                                   tuples where outcome is 0 or 1

        Returns:
            Brier score in range [0, 1]. Returns 0.0 if list is empty.
        """
        if not forecasts_and_outcomes:
            return 0.0

        sum_squared_errors = sum(
            (forecast - outcome) ** 2 for forecast, outcome in forecasts_and_outcomes
        )
        brier = sum_squared_errors / len(forecasts_and_outcomes)
        return brier

    def calibration_analysis(
        self, forecasts_and_outcomes: List[Tuple[float, int]]
    ) -> Dict[str, Any]:
        """Analyze calibration by binning forecasts into deciles.

        Deciles: [0-10%), [10-20%), ..., [90-100%]
        For each decile:
            - Compute mean forecast probability
            - Compute actual settlement rate
            - Check if actual rate is within [forecast - 5%, forecast + 5%]

        Args:
            forecasts_and_outcomes: List of (forecast_probability, actual_outcome) tuples

        Returns:
            Dict with structure:
            {
                "deciles": [
                    {
                        "decile_range": "0-10%",
                        "forecast_mean": float,
                        "actual_rate": float,
                        "count": int,
                        "within_tolerance": bool,
                    },
                    ...
                ]
            }
        """
        if not forecasts_and_outcomes:
            return {"deciles": []}

        # Bin forecasts into 10 deciles
        deciles: Dict[int, List[Tuple[float, int]]] = {i: [] for i in range(10)}

        for forecast, outcome in forecasts_and_outcomes:
            # Determine decile: clamp forecast to [0, 1] then bin
            clamped_forecast = max(0.0, min(1.0, forecast))
            decile_idx = min(9, int(clamped_forecast * 10))
            deciles[decile_idx].append((forecast, outcome))

        # Compute metrics for each decile
        decile_results = []
        for decile_idx in range(10):
            bin_data = deciles[decile_idx]
            if not bin_data:
                continue

            forecast_mean = sum(f for f, _ in bin_data) / len(bin_data)
            outcome_sum = sum(o for _, o in bin_data)
            actual_rate = outcome_sum / len(bin_data)
            within_tolerance = abs(actual_rate - forecast_mean) <= 0.05

            decile_results.append(
                {
                    "decile_range": f"{decile_idx * 10}-{(decile_idx + 1) * 10}%",
                    "forecast_mean": forecast_mean,
                    "actual_rate": actual_rate,
                    "count": len(bin_data),
                    "within_tolerance": within_tolerance,
                }
            )

        return {"deciles": decile_results}


class ReplaySimulator:
    """Simulate historical replay for backtesting and Brier score validation.

    Uses deterministic forecasts (market price + fixed offset) to avoid RNG
    and ensure reproducibility. Each run with same input produces same output.
    """

    def __init__(
        self,
        config: AppConfig,
        decision_engine: DecisionEngine,
        market_provider: MarketDataProvider,
        inference_service: Optional[InferenceService] = None,
    ) -> None:
        """Initialize replay simulator.

        Args:
            config: Application configuration
            decision_engine: DecisionEngine for evaluating trades
            market_provider: Market data provider (typically MockMarketDataProvider)
        """
        self.config = config
        self.decision_engine = decision_engine
        self.market_provider = market_provider
        self.brier_calculator = BrierScoreCalculator()
        self.inference_service = inference_service

        logger.info(
            "ReplaySimulator initialized",
            extra={
                "event_type": "replay_init",
                "actor": "replay_simulator",
            },
        )

    async def replay(self, market_id: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Run deterministic replay over historical market snapshots.

        For each snapshot in the time range:
        1. Fetch snapshot from market provider
        2. Generate deterministic forecast (market mid-price + 0.05 offset, clamped)
        3. Evaluate trade with DecisionEngine
        4. Record decision (timestamp, forecast, price, edge, decision, gate result)

        After processing all snapshots:
        5. Fetch settlement outcome from fixture data
        6. Calculate Brier score
        7. Calculate calibration analysis
        8. Return report with metrics

        Args:
            market_id: Kalshi market ID
            start_time: ISO8601 start timestamp (inclusive)
            end_time: ISO8601 end timestamp (inclusive)

        Returns:
            Dict with replay report containing:
            {
                "market_id": str,
                "period": {"start": str, "end": str},
                "total_snapshots": int,
                "total_decisions": int,
                "decisions": [
                    {
                        "decision_id": str,
                        "timestamp": str,
                        "forecast": float,
                        "market_price": float,
                        "edge": float,
                        "decision": str,
                        "risk_gate_result": str,
                    },
                    ...
                ],
                "settlement": {market settlement data or None},
                "metrics": {
                    "brier_score": float,
                    "brier_threshold": float,
                    "brier_pass": bool,
                    "calibration": {calibration dict},
                },
                "timestamp": str,
            }
        """
        trace_id = get_trace_id()

        # Fetch historical snapshots
        snapshots = await self.market_provider.get_historical_snapshots(
            market_id, start_time, end_time
        )

        logger.info(
            "Replay starting",
            extra={
                "trace_id": trace_id,
                "event_type": "replay_start",
                "actor": "replay_simulator",
                "market_id": market_id,
                "snapshot_count": len(snapshots),
            },
        )

        decisions = []
        forecasts_and_outcomes = []

        # Process each snapshot
        for snapshot in snapshots:
            # Compute market-implied probability (mid-price of YES)
            market_price = (snapshot.yes_bid + snapshot.yes_ask) / 2.0

            if self.inference_service is not None:
                inference = self.inference_service.posterior_probability(
                    market_id=snapshot.market_id,
                    market_prior=market_price,
                    evidence_items=[],
                )
                simulated_forecast = inference.probability
            else:
                # Deterministic forecast path retained for backward compatibility.
                simulated_forecast = min(1.0, max(0.0, market_price + 0.05))

            # Evaluate trade with DecisionEngine
            decision = self.decision_engine.evaluate_trade(
                snapshot,
                our_probability=simulated_forecast,
                gap_threshold_pct=0.05,
                max_position_usd=self.config.execution.max_position_usd,
                daily_loss_so_far=0.0,
            )

            # Record decision for report
            decisions.append(
                {
                    "decision_id": decision.decision_id,
                    "timestamp": snapshot.timestamp,
                    "forecast": simulated_forecast,
                    "market_price": market_price,
                    "edge": decision.edge,
                    "decision": decision.decision,
                    "risk_gate_result": decision.risk_gate_result,
                }
            )

        # Fetch settlement outcome from fixture
        settlement_data = await self._get_settlement_outcome(market_id)

        # Calculate Brier score if settlement exists
        if settlement_data and decisions:
            # Use final forecast from last decision
            final_forecast: float = decisions[-1]["forecast"]  # type: ignore
            actual_outcome = int(settlement_data.get("actual_outcome", 0))
            forecasts_and_outcomes.append((final_forecast, actual_outcome))

        brier = self.brier_calculator.calculate(forecasts_and_outcomes)
        calibration = self.brier_calculator.calibration_analysis(forecasts_and_outcomes)

        # Compile report
        report: Dict[str, Any] = {
            "market_id": market_id,
            "period": {"start": start_time, "end": end_time},
            "total_snapshots": len(snapshots),
            "total_decisions": len(decisions),
            "decisions": decisions,
            "settlement": settlement_data,
            "metrics": {
                "brier_score": brier,
                "brier_threshold": 0.19,  # Gate D locked threshold
                "brier_pass": brier < 0.19 if brier > 0 else False,
                "calibration": calibration,
            },
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            "Replay completed",
            extra={
                "trace_id": trace_id,
                "event_type": "replay_complete",
                "actor": "replay_simulator",
                "market_id": market_id,
                "total_snapshots": len(snapshots),
                "total_decisions": len(decisions),
                "brier_score": brier,
                "brier_pass": report["metrics"]["brier_pass"],
            },
        )

        return report

    async def _get_settlement_outcome(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get settlement outcome for a market from market provider fixtures.

        Args:
            market_id: Market ID to look up

        Returns:
            Settlement dict (with actual_outcome, settlement_price, timestamp) or None
        """
        # Access mock provider's settlement data directly
        # This is OK for testing; in production, would fetch from Kalshi API
        if hasattr(self.market_provider, "_settlement_data"):
            return self.market_provider._settlement_data.get(market_id)  # type: ignore
        return None
