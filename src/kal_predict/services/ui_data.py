"""Data aggregation helpers for read-only UI endpoints."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from kal_predict.adapters.market import (
    KalshiMarketDataProvider,
    MarketDataProvider,
    MockMarketDataProvider,
)
from kal_predict.config import AppConfig
from kal_predict.core.decision import DecisionEngine
from kal_predict.models import Decision
from kal_predict.services.inference import InferenceService
from kal_predict.storage.paper_store import PaperStore


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _project_root() -> Path:
    return Path(__file__).parent.parent.parent.parent


def _safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def _parse_iso(timestamp: Optional[str]) -> Optional[datetime]:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def freshness_seconds(timestamp: Optional[str]) -> int:
    parsed = _parse_iso(timestamp)
    if parsed is None:
        return -1
    now = datetime.now(timezone.utc)
    return max(0, int((now - parsed).total_seconds()))


def build_market_provider(config: AppConfig) -> tuple[MarketDataProvider, str]:
    """Build the read-only market provider and explicit source label."""
    if config.kalshi.is_available:
        private_key_pem = config.kalshi.load_private_key()
        if private_key_pem:
            return (
                KalshiMarketDataProvider(
                    api_key_id=str(config.kalshi.api_key_id),
                    private_key_pem=private_key_pem,
                    base_url=config.kalshi.base_url,
                ),
                "kalshi_read_only",
            )
    return MockMarketDataProvider(), "mock_market_provider"


class UIDataService:
    """Read-only service that maps runtime artifacts into API payloads."""

    def __init__(
        self,
        config: AppConfig,
        market_provider: MarketDataProvider | None = None,
        market_source: str | None = None,
    ) -> None:
        self._config = config
        self._root = _project_root()
        self._state_file = self._root / "data" / "heartbeat" / "state.json"
        self._replay_file = self._root / "data" / "replay_results.json"
        self._log_file = self._root / "logs" / "kal_predict.log"
        provider, source = build_market_provider(config)
        self._market_provider = market_provider or provider
        self._market_source = market_source or source
        self._decision_engine = DecisionEngine(config)
        self._inference = InferenceService(config)
        self._paper_store = PaperStore(config.paper_data.database_path)
        self._paper_store.initialize()
        self._trial_lock = Lock()
        self._trial_balance_usd = 10000.0
        self._trial_positions: dict[str, int] = {}
        self._trial_bets: list[dict[str, Any]] = []
        self._trial_traces: list[dict[str, Any]] = []

    async def health(self) -> dict[str, Any]:
        state = _safe_read_json(self._state_file, {})
        timestamp = state.get("timestamp")
        stale_alerts: list[str] = []
        f_secs = freshness_seconds(timestamp)
        if f_secs > 90:
            stale_alerts.append("heartbeat_stale")
        if f_secs < 0:
            stale_alerts.append("heartbeat_missing")

        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": f_secs,
            "source": "heartbeat_state",
            "mode": self._config.execution.mode,
            "heartbeat_status": state.get("status", "UNKNOWN"),
            "last_heartbeat_at": timestamp,
            "providers": {
                "kalshi": "credentialed" if self._config.kalshi.is_available else "mock",
                "nws": "configured",
                "search": "configured",
            },
            "inference": self._inference.health(),
            "stale_data_alerts": stale_alerts,
        }

    async def inference_health(self) -> dict[str, Any]:
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": 0,
            "source": "inference_runtime",
            "inference": self._inference.health(),
        }

    async def markets(self, limit: int) -> dict[str, Any]:
        market_ids = await self._market_provider.list_markets()
        items = []
        for market_id in market_ids[:limit]:
            snapshot = await self._market_provider.get_market_snapshot(market_id)
            if snapshot is None:
                continue
            spread = max(0.0, snapshot.yes_ask - snapshot.yes_bid)
            items.append(
                {
                    "market_id": snapshot.market_id,
                    "title": snapshot.title,
                    "yes_bid": snapshot.yes_bid,
                    "yes_ask": snapshot.yes_ask,
                    "no_bid": snapshot.no_bid,
                    "no_ask": snapshot.no_ask,
                    "volume": snapshot.volume,
                    "snapshot_timestamp": snapshot.timestamp,
                    "spread": spread,
                    "status": snapshot.status,
                    "close_time": snapshot.close_time,
                    "category_hint": snapshot.category_hint,
                    "liquidity": snapshot.liquidity,
                }
            )

        latest_ts = str(items[0]["snapshot_timestamp"]) if items else None
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": freshness_seconds(latest_ts),
            "source": self._market_source,
            "provider_status": (
                "credentialed" if self._market_source == "kalshi_read_only" else "mock"
            ),
            "markets": items,
        }

    async def decisions(self, limit: int, market_id: Optional[str]) -> dict[str, Any]:
        replay = _safe_read_json(self._replay_file, {})
        raw_decisions = replay.get("decisions", [])
        decisions = []
        for item in raw_decisions:
            d_market = replay.get("market_id", item.get("market_id", "UNKNOWN"))
            if market_id and d_market != market_id:
                continue
            decisions.append(
                {
                    "decision_id": item.get(
                        "decision_id",
                        f"decision-{item.get('timestamp', 'unknown')}",
                    ),
                    "market_id": d_market,
                    "mixed_probability": item.get("forecast", 0.0),
                    "market_implied_probability": item.get("market_price", 0.0),
                    "edge": item.get("edge", 0.0),
                    "risk_gate_result": item.get("risk_gate_result", "UNKNOWN"),
                    "decision": item.get("decision", "NO_TRADE"),
                    "trace_id": item.get("decision_id", "unknown-trace"),
                    "decision_timestamp": item.get("timestamp", ""),
                }
            )
            if len(decisions) >= limit:
                break

        newest_ts = decisions[0]["decision_timestamp"] if decisions else None
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": freshness_seconds(newest_ts),
            "source": "replay_results",
            "decisions": decisions,
        }

    async def replay_metrics(self) -> dict[str, Any]:
        replay = _safe_read_json(self._replay_file, {})
        metrics = replay.get("metrics", {})
        metric_ts = replay.get("timestamp")
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": freshness_seconds(metric_ts),
            "source": "replay_results",
            "brier_score": metrics.get("brier_score"),
            "brier_threshold": metrics.get("brier_threshold", 0.19),
            "brier_pass": metrics.get("brier_pass", False),
            "calibration_summary": metrics.get("calibration", {}),
            "last_replay_at": metric_ts,
        }

    async def paper_metrics(self) -> dict[str, Any]:
        metrics = self._paper_store.paper_metrics()
        if metrics["total_trades"] > 0 or metrics["risk_gate_failures"] > 0:
            return {
                "timestamp": utc_now_iso(),
                "freshness_seconds": freshness_seconds(metrics["last_trade_at"]),
                "source": "paper_store",
                **metrics,
            }

        replay = _safe_read_json(self._replay_file, {})
        decisions = replay.get("decisions", [])
        wins = 0
        losses = 0
        pnl = 0.0
        risk_failures = 0
        last_trade_at = None
        for item in decisions:
            action = item.get("decision", "NO_TRADE")
            edge = float(item.get("edge", 0.0))
            if item.get("risk_gate_result") == "FAIL":
                risk_failures += 1
            if action in {"BUY_YES", "BUY_NO"}:
                last_trade_at = item.get("timestamp", last_trade_at)
                if edge >= 0:
                    wins += 1
                else:
                    losses += 1
                pnl += edge * 100.0

        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": freshness_seconds(last_trade_at),
            "source": "replay_results",
            "paper_pnl": round(pnl, 2),
            "wins": wins,
            "losses": losses,
            "total_trades": wins + losses,
            "risk_gate_failures": risk_failures,
            "last_trade_at": last_trade_at,
        }

    async def audit(
        self, trace_id: Optional[str], level: Optional[str], limit: int
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        if self._log_file.exists():
            try:
                with open(self._log_file, "r", encoding="utf-8") as handle:
                    lines = handle.readlines()
            except OSError:
                lines = []
            for line in reversed(lines):
                entry_line = line.strip()
                if not entry_line:
                    continue
                try:
                    parsed = json.loads(entry_line)
                except json.JSONDecodeError:
                    continue
                event_trace = parsed.get("trace_id", "")
                event_level = str(parsed.get("level", "INFO")).upper()
                if trace_id and event_trace != trace_id:
                    continue
                if level and event_level != level.upper():
                    continue
                events.append(
                    {
                        "trace_id": event_trace or "unknown-trace",
                        "event_type": parsed.get("event_type", "log"),
                        "actor": parsed.get("actor", parsed.get("logger", "system")),
                        "status": parsed.get("status", "INFO"),
                        "message": parsed.get("message", ""),
                        "level": event_level,
                        "event_timestamp": parsed.get("timestamp", ""),
                    }
                )
                if len(events) >= limit:
                    break

        latest_ts = events[0]["event_timestamp"] if events else None
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": freshness_seconds(latest_ts),
            "source": "application_logs",
            "events": events,
        }

    async def trial_markets(self, limit: int) -> dict[str, Any]:
        """Temporary Kalshi-like trial feed from mock markets."""
        market_ids = await self._market_provider.list_markets()
        items = []
        for market_id in market_ids[:limit]:
            snapshot = await self._market_provider.get_market_snapshot(market_id)
            if snapshot is None:
                continue
            prior = (snapshot.yes_bid + snapshot.yes_ask) / 2.0
            inference = self._inference.posterior_probability(
                market_id=market_id,
                market_prior=prior,
                evidence_items=[
                    {
                        "claim": "NWS trend indicates elevated volatility for target region.",
                        "confidence_hint": 0.56,
                        "reliability_score": 0.74,
                    }
                ],
                role="hands",
            )
            items.append(
                {
                    "market_id": market_id,
                    "title": market_id.replace("_", " "),
                    "yes_price": round(snapshot.yes_ask, 4),
                    "no_price": round(snapshot.no_ask, 4),
                    "volume": snapshot.volume,
                    "implied_probability": round(prior, 4),
                    "forecast_probability": round(inference.probability, 4),
                    "inference_source": inference.source,
                    "inference_fallback_reason": inference.fallback_reason,
                    "inference_latency_ms": inference.latency_ms,
                    "model": inference.model,
                    "snapshot_timestamp": snapshot.timestamp,
                }
            )
        latest_ts = str(items[0]["snapshot_timestamp"]) if items else None
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": freshness_seconds(latest_ts),
            "source": "trial_exchange",
            "markets": items,
        }

    async def trial_book(self) -> dict[str, Any]:
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": 0,
            "source": "trial_exchange",
            "balance_usd": round(self._trial_balance_usd, 2),
            "positions": self._trial_positions,
            "bets": self._trial_bets[:100],
        }

    async def trial_decision_trace(self, limit: int) -> dict[str, Any]:
        latest_ts = self._trial_traces[0]["decision_timestamp"] if self._trial_traces else None
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": freshness_seconds(latest_ts),
            "source": "trial_exchange",
            "traces": self._trial_traces[:limit],
        }

    async def trial_manual_bet(self, market_id: str, side: str, contracts: int) -> dict[str, Any]:
        snapshot = await self._market_provider.get_market_snapshot(market_id)
        if snapshot is None:
            return self._error("market_not_found", "Market was not found.")
        if side not in {"YES", "NO"}:
            return self._error("invalid_side", "Side must be YES or NO.")
        if contracts <= 0:
            return self._error("invalid_contracts", "Contracts must be > 0.")
        price = snapshot.yes_ask if side == "YES" else snapshot.no_ask
        cost = round(price * contracts * 100.0, 2)
        implied = (snapshot.yes_bid + snapshot.yes_ask) / 2.0
        if side == "YES":
            inferred = max(implied, min(1.0, self._decision_engine.min_confidence + 0.01))
        else:
            inferred = max(implied, min(1.0, self._decision_engine.min_confidence + 0.01))
        if cost > self._trial_balance_usd:
            return self._error("insufficient_balance", "Insufficient trial balance.")
        evaluation = self._evaluate_decision(
            snapshot=snapshot,
            inferred_probability=inferred,
            inference_source="manual",
            inference_fallback_reason=None,
            inference_latency_ms=0,
            model="operator-manual",
            contracts=contracts,
            gap_threshold_pct=0.05,
        )
        decision = evaluation["decision"]
        if decision.risk_gate_result == "FAIL":
            return self._error(
                "risk_gate_failed",
                "Risk gate blocked this paper action.",
                details={"trace": evaluation["trace"]},
            )
        execute = self._execute_paper_bet(
            mode="manual",
            market_id=market_id,
            side=side,
            contracts=contracts,
            price=price,
        )
        if not execute.get("ok"):
            return execute
        self._record_durable_paper_bet(
            decision=decision,
            market_id=market_id,
            side=side,
            contracts=contracts,
            price=price,
            bet=execute["bet"],
        )
        self._trial_traces.insert(0, evaluation["trace"])
        return execute

    async def trial_auto_bet(self, market_id: str, contracts: int) -> dict[str, Any]:
        snapshot = await self._market_provider.get_market_snapshot(market_id)
        if snapshot is None:
            return self._error("market_not_found", "Market was not found.")
        if contracts <= 0:
            return self._error("invalid_contracts", "Contracts must be > 0.")

        prior = (snapshot.yes_bid + snapshot.yes_ask) / 2.0
        inference = self._inference.posterior_probability(
            market_id=market_id,
            market_prior=prior,
            evidence_items=[
                {
                    "claim": "NWS update suggests warmer than baseline conditions.",
                    "confidence_hint": 0.61,
                    "reliability_score": 0.81,
                }
            ],
            role="hands",
        )
        evaluation = self._evaluate_decision(
            snapshot=snapshot,
            inferred_probability=inference.probability,
            inference_source=inference.source,
            inference_fallback_reason=inference.fallback_reason,
            inference_latency_ms=inference.latency_ms,
            model=inference.model,
            contracts=contracts,
            gap_threshold_pct=0.05,
        )
        decision = evaluation["decision"]
        if decision.risk_gate_result == "FAIL":
            return self._error(
                "risk_gate_failed",
                "Risk gate blocked this auto paper action.",
                details={"trace": evaluation["trace"]},
            )
        if decision.decision not in {"BUY_YES", "BUY_NO"}:
            return self._error(
                "no_trade_signal",
                "Decision engine returned NO_TRADE for auto action.",
                details={"trace": evaluation["trace"]},
            )
        side = "YES" if decision.decision == "BUY_YES" else "NO"
        price = snapshot.yes_ask if side == "YES" else snapshot.no_ask
        result = self._execute_paper_bet(
            mode="auto",
            market_id=market_id,
            side=side,
            contracts=contracts,
            price=price,
        )
        if result.get("ok"):
            self._record_durable_paper_bet(
                decision=decision,
                market_id=market_id,
                side=side,
                contracts=contracts,
                price=price,
                bet=result["bet"],
            )
            self._trial_traces.insert(0, evaluation["trace"])
        return result

    async def run_trial_scenarios(
        self, scenarios: list[dict[str, Any]], dry_run: bool = True
    ) -> dict[str, Any]:
        """Run bounded pre-key scenario simulations with paper-only semantics."""
        bounded = scenarios[:20]
        summary: dict[str, Any] = {
            "total": len(bounded),
            "pass": 0,
            "fail": 0,
            "no_trade": 0,
            "fallback_count": 0,
            "results": [],
        }
        for scenario in bounded:
            market_id = str(scenario.get("market_id", ""))
            mode = str(scenario.get("mode", "auto")).lower()
            contracts = int(scenario.get("contracts", 1))
            if dry_run:
                res = await self._simulate_scenario(
                    market_id=market_id,
                    mode=mode,
                    contracts=contracts,
                    side=scenario.get("side"),
                )
            else:
                if mode == "manual":
                    side = str(scenario.get("side", "YES")).upper()
                    res = await self.trial_manual_bet(
                        market_id=market_id, side=side, contracts=contracts
                    )
                else:
                    res = await self.trial_auto_bet(market_id=market_id, contracts=contracts)
            if res.get("ok"):
                summary["pass"] += 1
            else:
                summary["fail"] += 1
                if res.get("error_code") == "no_trade_signal":
                    summary["no_trade"] += 1
            trace = (res.get("details") or {}).get("trace")
            if trace and trace.get("inference_source") == "fallback":
                summary["fallback_count"] += 1
            summary["results"].append(res)
        return {
            "timestamp": utc_now_iso(),
            "freshness_seconds": 0,
            "source": "trial_exchange",
            "dry_run": dry_run,
            "summary": summary,
        }

    async def _simulate_scenario(
        self, market_id: str, mode: str, contracts: int, side: Any = None
    ) -> dict[str, Any]:
        snapshot = await self._market_provider.get_market_snapshot(market_id)
        if snapshot is None:
            return self._error("market_not_found", "Market was not found.")
        prior = (snapshot.yes_bid + snapshot.yes_ask) / 2.0
        if mode == "manual":
            normalized_side = str(side or "YES").upper()
            inferred = (
                min(1.0, prior + 0.05)
                if normalized_side == "YES"
                else max(0.0, prior - 0.05)
            )
            evaluation = self._evaluate_decision(
                snapshot=snapshot,
                inferred_probability=inferred,
                inference_source="manual",
                inference_fallback_reason=None,
                inference_latency_ms=0,
                model="operator-manual",
                contracts=contracts,
                gap_threshold_pct=0.05,
            )
        else:
            inference = self._inference.posterior_probability(
                market_id=market_id,
                market_prior=prior,
                evidence_items=[
                    {
                        "claim": "Scenario-mode weather stress case.",
                        "confidence_hint": 0.58,
                        "reliability_score": 0.78,
                    }
                ],
                role="hands",
            )
            evaluation = self._evaluate_decision(
                snapshot=snapshot,
                inferred_probability=inference.probability,
                inference_source=inference.source,
                inference_fallback_reason=inference.fallback_reason,
                inference_latency_ms=inference.latency_ms,
                model=inference.model,
                contracts=contracts,
                gap_threshold_pct=0.05,
            )
        decision = evaluation["decision"]
        if decision.risk_gate_result == "FAIL":
            return self._error(
                "risk_gate_failed",
                "Risk gate blocked scenario.",
                details={"trace": evaluation["trace"]},
            )
        if decision.decision == "NO_TRADE":
            return self._error(
                "no_trade_signal",
                "Decision engine returned NO_TRADE for scenario.",
                details={"trace": evaluation["trace"]},
            )
        return {"ok": True, "simulated": True, "trace": evaluation["trace"]}

    def _execute_paper_bet(
        self,
        mode: str,
        market_id: str,
        side: str,
        contracts: int,
        price: float,
    ) -> dict[str, Any]:
        cost = round(price * contracts * 100.0, 2)
        with self._trial_lock:
            if cost > self._trial_balance_usd:
                return self._error("insufficient_balance", "Insufficient trial balance.")
            self._trial_balance_usd -= cost
            signed = contracts if side == "YES" else -contracts
            self._trial_positions[market_id] = self._trial_positions.get(market_id, 0) + signed
            bet = {
                "bet_id": f"trial-{uuid.uuid4().hex[:12]}",
                "mode": mode,
                "market_id": market_id,
                "side": side,
                "contracts": contracts,
                "price": round(price, 4),
                "cost_usd": cost,
                "placed_at": utc_now_iso(),
            }
            self._trial_bets.insert(0, bet)
            balance = round(self._trial_balance_usd, 2)
        return {"ok": True, "bet": bet, "balance_usd": balance}

    def _record_durable_paper_bet(
        self,
        decision: Decision,
        market_id: str,
        side: str,
        contracts: int,
        price: float,
        bet: dict[str, Any],
    ) -> None:
        fill = {
            "fill_id": bet["bet_id"],
            "decision_id": decision.decision_id,
            "market_id": market_id,
            "side": side,
            "fill_price": price,
            "size": contracts * 100,
            "fees": 0.0,
            "timestamp": bet["placed_at"],
            "trace_id": decision.trace_id,
        }
        self._paper_store.record_decision_and_fill(decision, fill)

    def _evaluate_decision(
        self,
        snapshot: Any,
        inferred_probability: float,
        inference_source: str,
        inference_fallback_reason: Optional[str],
        inference_latency_ms: int,
        model: str,
        contracts: int,
        gap_threshold_pct: float,
    ) -> dict[str, Any]:
        decision = self._decision_engine.evaluate_trade(
            market_snapshot=snapshot,
            our_probability=inferred_probability,
            gap_threshold_pct=gap_threshold_pct,
            max_position_usd=float(contracts * 100),
            daily_loss_so_far=0.0,
        )
        trace = {
            "trace_id": decision.trace_id,
            "market_id": snapshot.market_id,
            "decision": decision.decision,
            "risk_gate_result": decision.risk_gate_result,
            "edge": round(decision.edge, 4),
            "expected_value": round(decision.expected_value, 4),
            "inferred_probability": round(inferred_probability, 4),
            "implied_probability": round(decision.market_implied_probability, 4),
            "inference_source": inference_source,
            "inference_fallback_reason": inference_fallback_reason,
            "inference_latency_ms": inference_latency_ms,
            "model": model,
            "gate_context": {
                "min_confidence": self._decision_engine.min_confidence,
                "max_position_usd": self._decision_engine.config.execution.max_position_usd,
                "daily_loss_limit_usd": self._decision_engine.daily_loss_limit,
                "gap_threshold_pct": gap_threshold_pct,
            },
            "decision_timestamp": utc_now_iso(),
        }
        return {"decision": decision, "trace": trace}

    def _error(
        self, error_code: str, message: str, details: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        payload = {
            "ok": False,
            "error_code": error_code,
            "message": message,
            "timestamp": utc_now_iso(),
            "trace_id": f"trial-{uuid.uuid4().hex[:8]}",
        }
        if details:
            payload["details"] = details
        return payload
