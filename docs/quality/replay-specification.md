# Replay Harness Specification

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Purpose

Define the replay harness (backtesting framework) for validating decision engine accuracy on historical market data before live trading or paper mode deployment.

## Replay Workflow

### Data Input

**Market snapshots with historical data:**
- Market ID, timestamp, yes_bid, yes_ask, no_bid, no_ask, volume
- Sample period: past 30-90 days of Kalshi weather contract data
- Sources: Kalshi API (historical read) or cached test fixtures

**Evidence corpus:**
- Time-stamped news headlines, weather reports, economic data
- Retrieved from archives (NWS historical data, news APIs)
- Synchronized with market snapshots by timestamp

### Replay Loop

```
for each market_snapshot in historical_data:
  1. Load all evidence available up to snapshot.timestamp
  2. Run Brain/Hands decision pipeline (identical to live code)
  3. Compute probability estimate (prior, model posterior, mixed)
  4. Compute edge (AI estimate vs market price)
  5. Evaluate risk gates (confidence, position sizing)
  6. Generate trade intent (if edge > threshold)
  7. Simulate fill: match snapshot bid/ask, deduct fees
  8. Record decision with trace ID and actual outcome
  9. When contract settles, compute Brier score contribution
```

### Output

**Decision trace:**
- Market ID, timestamp, prior_probability, model_probability, mix_alpha, mixed_probability
- Market implied probability, edge, risk gate result, trade decision
- Simulated fill price, simulated PnL
- Trace ID for audit trail

**Brier score calculation (post-settlement):**
```
brier_score_i = (forecast_probability_i - actual_outcome_i)^2
overall_brier = mean(brier_score_i for all forecasts)
```

**Calibration analysis:**
- Bin forecasts by decile (0-10%, 10-20%, ..., 90-100%)
- For each bin, compute actual settlement rate
- Plot reliability curve: forecasted vs actual
- Tolerance: actual rates within ±5% of forecast decile

## Pass/Fail Criteria

### Brier Score Thresholds

**By contract category:**
- **Weather markets:** Brier < 0.18 (60% avg accuracy equivalent)
- **Economic markets:** Brier < 0.20 (55% avg accuracy equivalent)
- **Overall portfolio:** Brier < 0.19 (weighted across all trades)

**Baseline comparison:**
- Must show improvement over market-implied probabilities
- Market baseline Brier: typically 0.20-0.22 for prediction markets
- Target: 5-10% better than baseline

### Calibration Thresholds

**Reliability curve tolerance:** ±5% deviation from perfect calibration
- Example: if model forecasts 70%, expect 65-75% actual settlement rate
- Detected via KS (Kolmogorov-Smirnov) test: p-value > 0.05

**No systematic bias:**
- Model must not consistently over/under-predict YES outcomes
- Symmetry test: |over-predictions| ≈ |under-predictions|

## Replay Harness Implementation

### Framework

**Language:** Python 3.9+  
**Location:** `src/kal_predict/core/replay.py`  
**Test location:** `tests/integration/test_replay.py`

**Key components:**
1. `HistoricalDataLoader` — Load market snapshots and evidence from files/API
2. `ReplaySimulator` — Execute decision pipeline on each snapshot
3. `FillSimulator` — Simulate order execution using historical bid/ask
4. `BrierScoreCalculator` — Post-settlement accuracy computation
5. `CalibrationAnalyzer` — Reliability curve generation

### Determinism Requirement

Replay must be **fully deterministic and reproducible:**
- Same input data → same output every run
- No randomness in decision path (all LLM calls must use same seed or cached responses)
- All timestamps and state preserved in trace logs

### Fixtures and Test Data

**Location:** `tests/fixtures/replay_data/`

**Minimal test set (for continuous integration):**
- 10 historical market snapshots
- 30 evidence items (news, weather, economic)
- Known expected Brier score for regression testing

**Comprehensive validation set (for Gate D/E approval):**
- 90 days of market data
- 500+ evidence items
- Expected to show Brier < 0.19 and calibration within tolerance

## Replay Report Format

### JSON Structure

```json
{
  "replay_run": {
    "timestamp": "2026-04-23T00:00:00Z",
    "data_period": "2026-01-23 to 2026-04-23",
    "total_markets": 50,
    "total_trades": 35,
    "metrics": {
      "brier_score": 0.175,
      "brier_by_category": {
        "weather": 0.168,
        "economic": 0.185
      },
      "calibration": {
        "ks_statistic": 0.042,
        "p_value": 0.12,
        "status": "PASS (within tolerance)"
      },
      "edge_distribution": {
        "mean_edge_pct": 7.3,
        "median_edge_pct": 5.8,
        "max_edge_pct": 18.2
      }
    },
    "trade_summary": {
      "total_win_trades": 22,
      "total_loss_trades": 13,
      "win_rate": 0.63,
      "avg_win": 45.50,
      "avg_loss": -38.20,
      "gross_pnl": 1467.50
    },
    "risk_gate_summary": {
      "confidence_gate_triggers": 8,
      "position_size_gate_triggers": 3,
      "daily_loss_gate_triggers": 0,
      "total_gates_passed": 35,
      "total_gates_failed": 0
    }
  }
}
```

### Human-Readable Report

Markdown summary with:
- Executive summary (pass/fail on Brier and calibration)
- Metrics table
- Trade performance breakdown
- Risk gate enforcement verification
- Reliability curve ASCII plot
- Recommendations for parameter tuning

## Gate D Completion Criteria

Replay harness is deemed complete when:

1. **Specification approved** (this document)
2. **Implementation complete** — `replay.py` and `test_replay.py` created
3. **Test fixtures available** — Minimal and comprehensive datasets
4. **Brier score threshold passed** — Portfolio Brier < 0.19 on comprehensive data
5. **Calibration threshold passed** — KS test p-value > 0.05
6. **No data leakage** — Replay only uses evidence available at decision time
7. **Reproducibility verified** — Same run produces identical results (seed locked)

Once all criteria met, Gate D is cleared and Gate E (Paper Release Ready) entry begins.

## References

- **Test Strategy:** `docs/quality/test-strategy.md`
- **Data Contracts:** `docs/architecture/data-contracts.md`
- **Bayesian Logic:** `src/kal_predict/core/decision.py` (when implemented)
- **Brier Score Literature:** Jolliffe, I.T., Stephenson, D.B. (2003). Forecast verification: a practitioner's guide in atmospheric science
