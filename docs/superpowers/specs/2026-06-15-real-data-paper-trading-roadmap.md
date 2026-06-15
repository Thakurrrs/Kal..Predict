# Real-Data Paper Trading Roadmap

## Purpose

Move Kal..Predict from a mock/trial dashboard into real-data paper trading, then into category-specific model training, and only later into gated live trading.

This roadmap keeps live trading disabled until the system has proven read-only data ingestion, durable paper accounting, outcome labeling, model evaluation, and operational safety.

## North Star

Build a system that can:

1. Read real Kalshi markets.
2. Classify supported markets into weather, economics, and soccer.
3. Fetch real supporting research for each category.
4. Produce auditable TRADE or SKIP decisions.
5. Paper trade only when strict gates pass.
6. Store every source, feature, decision, fill, skip, and outcome.
7. Train category-specific models on real settled outcomes.
8. Promote to live trading only after paper/live parity and profitability gates pass.

## Category Scope

### Weather

Use weather as an audit-proof source-backed category. It is good for proving source freshness, deterministic parsing, cache behavior, and contract-specific research.

Initial supported markets:

- Temperature threshold markets.
- Rain/snow threshold markets.
- Clearly parseable location/date/weather-condition contracts.

Initial exclusions:

- Ambiguous title-only contracts.
- Compound weather conditions.
- Markets without clear location and resolution window.

### Economics

Use economics as a low-frequency macro category with authoritative sources.

Initial supported markets:

- CPI/inflation release markets.
- Federal Reserve rate decision markets.
- Unemployment or jobs report markets if a reliable source and release calendar are available.

Initial exclusions:

- Ambiguous political/economic narrative markets.
- Markets whose outcome depends on interpretation rather than a published number.

### Soccer

Use soccer as the high-volume, real-feeling sports category. Soccer should accelerate paper-trading UX, settlement feedback, and future model-training volume.

Initial supported markets:

- Team wins match.
- Team advances or qualifies.
- Tournament winner if contract parsing is reliable.

Initial exclusions:

- Exact score.
- Player props.
- Cards/corners/shots.
- Live/in-game markets.
- Parlays or compound conditional markets.
- Any market where draw handling is unclear.

## Milestones

### Milestone 1: Real Read-Only Market Feed

Replace mock market display with real Kalshi read-only market data.

Status as of 2026-06-15:

- Provider selection is implemented: real Kalshi read-only is used when credentials and private key are configured; otherwise the app falls back to an explicitly labeled mock provider.
- `/api/ui/markets` now exposes `source` and `provider_status` so the UI cannot silently present mock data as real.
- The Market Prices UI now shows source, provider status, status, close time, title/category hint, liquidity, spread, and volume.
- Authenticated Kalshi smoke against real credentials is still required before this milestone is fully complete.

Success criteria:

- Dashboard shows real market IDs, prices, spreads, volume, close time, and status.
- UI labels data as real Kalshi read-only.
- No live order path is enabled.
- Unsupported markets are visible as skipped or unsupported, not hidden silently.

### Milestone 2: Real Category Routing

Classify real Kalshi markets into weather, economics, soccer, unsupported, or unsafe.

Success criteria:

- Category router produces deterministic category and parser status.
- Supported market contracts include parsed fields needed for research.
- Unsupported markets receive explicit skip reasons.

### Milestone 3: Real Source-Backed Research

Fetch category-specific real research and persist it through `SourceCache`.

Success criteria:

- Weather uses NWS or another authoritative weather source.
- Economics uses FRED/BLS/Fed release sources as appropriate.
- Soccer uses structured fixture/team/result data from a reliable source.
- Every source has health, freshness, cache status, and provenance.

### Milestone 4: Audit-Quality Paper Decisions

Run deterministic decision gates on real market and research snapshots.

Success criteria:

- Every market gets a TRADE or SKIP decision.
- Every skip has a primary reason.
- Paper fills only occur after all gates pass.
- Paper decisions and fills are durable in SQLite.

### Milestone 5: Outcome Labeling

Poll or ingest final market outcomes and settle paper fills.

Success criteria:

- Outcomes are linked to fills and market IDs.
- Realized PnL is calculated from stored fills.
- Canceled/unresolved markets are handled without false wins/losses.

### Milestone 6: Training Dataset Builder

Turn observed real markets into clean category-specific training rows.

Success criteria:

- Training rows include market snapshot, parsed contract, source features, model prediction, decision, outcome, and timestamps.
- Skipped markets are included, not only traded markets.
- Features are timestamp-safe and cannot leak future information.

### Milestone 7: Category-Specific Baseline Models

Add separate model slots for weather, economics, and soccer.

Success criteria:

- Each category model has its own feature schema.
- Baselines are evaluated against market-implied probabilities.
- Model predictions are versioned and stored before outcomes are known.

### Milestone 8: Model-Assisted Paper Trading

Use category model predictions in paper mode only.

Success criteria:

- Decision engine still owns risk.
- Models estimate probability; gates decide whether to trade.
- Paper performance is compared against baseline and market-implied probabilities.

### Milestone 9: Live Readiness

Prepare for live trading only after paper mode proves reliable.

Success criteria:

- Paper/live parity tests pass.
- Kill switch is tested.
- Position reconciliation is tested.
- Order placement/cancel dry runs are tested.
- Required paper sample size and profitability/calibration gates are met.

## Non-Goals Until Explicit Approval

- No live trading.
- No autonomous live order placement.
- No broad unsupported category trading.
- No training on post-outcome leaked features.
- No claims of profitability from small paper samples.
