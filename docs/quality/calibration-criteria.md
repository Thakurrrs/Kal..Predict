# Calibration and Pass Criteria (Locked for Gate D)

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved and LOCKED

## Purpose

Formally define and lock the Brier score and calibration thresholds required to pass Gate D (Verification Ready) and Gate E (Paper Release Ready). These criteria are **immutable for this phase** and serve as the acceptance criteria for live trading consideration.

## Brier Score Definition and Thresholds

### Definition

**Brier Score** measures the mean squared error of probability forecasts:

```
BS = (1/N) * Σ(f_i - o_i)²

where:
  f_i = forecasted probability for event i (0 to 1)
  o_i = actual outcome (1 if YES, 0 if NO)
  N = total number of forecasts
```

**Interpretation:**
- Brier = 0: Perfect forecasts (impossible in practice)
- Brier = 0.25: Random forecasting (50/50 predictions)
- Brier = 0.50: Maximally poor forecasting (always wrong)

### Locked Thresholds (Gate D Exit)

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| **Overall Portfolio Brier** | < 0.190 | 60% equivalent accuracy |
| **Weather Markets Brier** | < 0.170 | Highest confidence category |
| **Economic Markets Brier** | < 0.195 | Higher volatility/uncertainty |
| **Improvement vs Market** | 5-10% better than baseline | Market baseline typically 0.20-0.22 |

**Baseline Justification:**
- Kalshi market-implied probabilities have observed Brier ~ 0.20-0.22
- 60% forecast accuracy (Brier 0.19) exceeds efficient market expectation
- Safety margin: 5-10% buffer before live trading authorization

### Locked Thresholds (Gate E Entry - Paper Release)

**Same thresholds apply:**
- Overall: < 0.190
- Weather: < 0.170
- Economic: < 0.195

**Additional requirement:**
- Stability across 24+ hour paper trading run (no degradation)
- No Brier score drift > 0.02 per 7 days of operation

## Calibration Criteria (Locked)

### Reliability Curve Definition

A forecast is **calibrated** if, across all predictions at probability level p%, the actual frequency of YES outcomes is approximately p%.

**Example:**
- All predictions with 70% confidence → should see ~70% YES outcomes
- All predictions with 40% confidence → should see ~40% YES outcomes

### Locked Acceptance Criteria

| Test | Threshold | Method |
|------|-----------|--------|
| **Kolmogorov-Smirnov (KS) Test** | p-value > 0.05 | Statistical test for distribution match |
| **Decile Tolerance** | ±5% per decile | Actual rate within [p-5%, p+5%] |
| **No Systematic Bias** | Symmetry ratio 0.8-1.2 | Over-predictions / Under-predictions |
| **Calibration Slope** | 0.85 ≤ slope ≤ 1.15 | Linear fit of (forecast vs actual) |

### Calibration Failure Modes

**FAIL conditions (block Gate D → E transition):**
1. KS test p-value ≤ 0.05 (statistically significant miscalibration)
2. Any decile > ±5% deviation (e.g., forecast 50%, observe 58%)
3. Systematic over-prediction (>30% more over than under)
4. Calibration slope outside 0.85-1.15 (severe over/under-confidence)

**WARN conditions (allow with documentation):**
- Edge case: Single decile with small sample size (n < 10) exceeds tolerance
- Action: Document and require larger sample (n > 30) for that decile before live

## Locked Gate D → E Transition Rules

### Gate D Exit (Verification Ready) - LOCKED

**Must pass:**
- ✅ Replay harness specification approved (`docs/quality/replay-specification.md`)
- ✅ Brier score < 0.190 (portfolio) on 30-day replay dataset
- ✅ Calibration: KS test p > 0.05 on same dataset
- ✅ All deciles within ±5% tolerance
- ✅ Zero manual override points in risk gate code
- ✅ Deterministic replay verified (reproducible runs)

**Evidence required:**
- Replay report (JSON + markdown) with metrics
- Calibration plot (reliability curve) with passing test
- Source data manifest (market snapshots, evidence items)
- Git commit with replay.py and test_replay.py

### Gate E Entry (Paper Release Ready) - LOCKED

**Must continue passing all Gate D criteria PLUS:**
- ✅ 24+ hours continuous paper trading with zero risk gate bypasses
- ✅ Brier score does NOT degrade > 0.02 during paper run
- ✅ No unexpected "hallucinated" decisions or nonsensical trades
- ✅ Incident response runbook validated (tabletop exercise)
- ✅ Kill switch tested and working (manual pause + restart)

**Evidence required:**
- 24h+ paper trading log with all decisions, fills, PnL
- Real-time market data integration verified (NWS, search working)
- Risk gate enforcement log (no violations)
- Runbook tabletop exercise notes and sign-off

## Immutability and Change Control

**These criteria are LOCKED as of 2026-04-23.**

**To modify thresholds:**
1. Document the specific reason (e.g., "market conditions changed", "new evidence suggests X")
2. Create an ADR (Architecture Decision Record) proposing the change
3. Founder approval required
4. New criteria must not be less stringent (e.g., Brier 0.20 is acceptable, 0.21+ is not)
5. Replay must be re-run with new thresholds before any gate transition

**Acceptable modifications:**
- Tightening thresholds (e.g., Brier 0.185 instead of 0.190)
- Adding more stringent calibration tests
- Extending minimum sample sizes

**Not acceptable:**
- Lowering standards mid-phase
- Retroactive changes to historic pass/fail decisions

## Metric Tracking and Approval Chain

### Per-Run Approval

**Gate D validation runs:**
1. Implementer runs replay, generates report
2. Founder reviews metrics against locked criteria
3. Founder approves or requires fixes + rerun
4. Once approved: Gate D cleared, proceed to Gate E

**Gate E validation runs:**
1. Paper trading loop runs 24+ hours
2. Founder monitors key metrics daily
3. At 24h mark: Founder reviews for drift, risk violations
4. Founder approves or extends observation window
5. Once approved: Gate E cleared, limited live authorization available

### Historical Log

**Location:** `tests/reports/gate-validation-log.md`

**Entry format:**
```markdown
## Gate D Validation - Run #1 (2026-04-24)
- Date: 2026-04-24
- Data period: 2026-01-24 to 2026-04-24
- Brier score: 0.187 ✓ (threshold 0.190)
- Calibration KS p-value: 0.068 ✓ (threshold > 0.05)
- Reviewer: Founder
- Approval: PASS
- Notes: Weather outperformed (0.165), economic slightly above target (0.192 vs 0.195)
```

## References

- **Brier, G.W.** (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review*, 78(1), 1-3.
- **Jolliffe, I.T., & Stephenson, D.B.** (2003). Forecast Verification: A Practitioner's Guide in Atmospheric Science. Wiley.
- **Test Strategy:** `docs/quality/test-strategy.md`
- **Replay Specification:** `docs/quality/replay-specification.md`
- **SDLC Charter:** `docs/governance/sdlc-charter.md`
