# Category Model Architecture

## Purpose

Define how Kal..Predict should support separate models for weather, economics, and soccer while keeping one global decision engine responsible for risk.

The core principle is: category models estimate probabilities; the decision engine decides whether risking paper capital is allowed.

## High-Level Architecture

```text
Kalshi market feed
  -> MarketCategoryRouter
  -> Category contract parser
  -> Category research fetcher
  -> Feature builder
  -> Category probability model
  -> DecisionEngine
  -> PaperStore
  -> Outcome labeler
  -> Training dataset builder
```

## Category Models

### WeatherProbabilityModel

Purpose:

- Estimate probability for weather threshold markets.

Inputs:

- Parsed location.
- Parsed weather variable.
- Threshold.
- Resolution window.
- NWS forecast values.
- Historical climatology if available.
- Kalshi implied probability.
- Spread, liquidity, and time to close.

Early baseline:

- Deterministic forecast-threshold comparison.
- Calibration layer against market-implied probability.

### EconomicsProbabilityModel

Purpose:

- Estimate probability for macro release and Fed decision markets.

Inputs:

- Release type.
- Consensus estimate if available.
- Prior release values.
- FRED/BLS/Fed source data.
- Time to release.
- Kalshi implied probability.
- Spread, liquidity, and time to close.

Early baseline:

- Market-implied probability plus rule-based source adjustments.
- Later: logistic or gradient-boosted model once enough labeled rows exist.

### SoccerProbabilityModel

Purpose:

- Estimate probability for soccer match, advancement, and tournament outcome markets.

Inputs:

- Parsed teams.
- Market type.
- Match date and competition.
- Home/away/neutral flag if known.
- Team strength rating.
- Recent form.
- Rest days.
- Injury/lineup data if reliable.
- Draw handling rule.
- Kalshi implied probability.
- Spread, liquidity, and time to close.

Early baseline:

- ELO-style team rating or external probability baseline.
- Calibration against market-implied probability.

## Global Decision Engine

The decision engine remains category-agnostic for core risk gates.

Responsibilities:

- Compare model probability against executable market price.
- Adjust for spread, fees, and slippage.
- Enforce minimum edge.
- Enforce source freshness.
- Enforce confidence requirements.
- Enforce max position size.
- Enforce daily/category/series exposure caps.
- Produce deterministic skip reasons.
- Decide TRADE or SKIP.

The decision engine must never trust a model enough to bypass gates.

## Data Capture

Every observed market should create durable records, even if skipped.

Required records:

- Raw Kalshi market snapshot.
- Parsed contract result.
- Category classification.
- Source research snapshot.
- Source cache metadata.
- Feature vector.
- Model prediction.
- Decision trace.
- Paper fill if traded.
- Outcome label after settlement.

## Training Rules

Models must train on real observed outcomes, not on their own choices.

Training data must include:

- Traded markets.
- Skipped markets.
- Markets close to trade thresholds.
- Repeated snapshots over time when available.

Strict leakage rules:

- Features must be available at prediction time.
- Closing price can be used as an evaluation target, not as a pre-trade feature unless timestamped before prediction.
- Final outcome must only be joined after settlement.
- Model version and feature schema version must be stored with every prediction.

## Evaluation Metrics

Probability quality:

- Brier score.
- Log loss.
- Calibration by probability bucket.

Trading quality:

- Paper PnL.
- ROI on committed exposure.
- Max drawdown.
- Win/loss count.
- Average edge at entry.
- Closing-line value where available.

Safety quality:

- Gate failure counts.
- Source stale counts.
- Parser failure counts.
- Unsupported market counts.
- Manual override count.

## Promotion Gates

A model can move from observation to paper-assisted mode only if:

- It has enough settled examples for the category.
- It beats the market-implied baseline out of sample.
- It is acceptably calibrated.
- It does not depend on leaked features.
- Paper decisions remain explainable and reproducible.

A model can move toward live readiness only after:

- Paper-assisted mode has a meaningful sample size.
- PnL is positive after fees/spread assumptions.
- Drawdown remains inside limits.
- Live execution safety tests pass.
- The operator explicitly approves live mode.

## Design Position

Kal..Predict should be designed now for category-specific models, but the first implementation should prioritize clean data collection and baseline probability models. Heavy model training should wait until we have enough settled, timestamp-safe real data.

