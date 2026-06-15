# Real-Data Paper Trading To Model Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build from real read-only Kalshi markets to real-data paper trading across weather, economics, and soccer, then collect training-grade data for category-specific models.

**Architecture:** Keep live trading disabled. Add real market ingestion, strict category parsing, source-backed research, durable paper decisions, outcome labeling, and training dataset generation in separate phases. Category models estimate probability, while the global decision engine owns risk gates and trade/skip decisions.

**Tech Stack:** Python 3.11, FastAPI, SQLite, Pydantic v2, pytest, Ruff, mypy, Next.js, TypeScript, Vitest.

---

## Phase 1: Real Kalshi Read-Only Market Feed

**Goal:** Replace mock market display with real read-only Kalshi market data while keeping all execution paper-only.

**Status as of 2026-06-15:** Partially complete. The code now selects `KalshiMarketDataProvider` when credentials and private key are configured, otherwise it falls back to an explicitly labeled mock provider. The UI/API market contract now exposes source, provider status, status, close time, title, category hint, and liquidity. Authenticated Kalshi smoke remains open because real credentials were not active in this session.

- [ ] Add authenticated Kalshi read-only smoke tests.
- [x] Add a market feed adapter that returns normalized `MarketSnapshot` objects.
- [x] Add provider source/status labeling for Kalshi read API availability.
- [x] Update UI market screens to show market source, status, close time, spread, volume, title, category hint, and liquidity.
- [x] Preserve mock provider as an explicit fallback when credentials are absent.
- [x] Verify no live order endpoint or live execution path is enabled.

Exit criteria:

- Dashboard can show normalized market snapshots and will use real Kalshi read-only data when credentials are configured.
- `/api/ui/markets` reports `source=kalshi_read_only` and `provider_status=credentialed` when keys are present; it reports `source=mock_market_provider` and `provider_status=mock` otherwise.
- No paper trade is placed from real data yet.
- Remaining gate: run authenticated Kalshi read-only smoke with real credentials and capture evidence.

## Phase 2: Category Router For Weather, Economics, Soccer

**Goal:** Classify real markets into supported categories with explicit skip reasons.

**Status as of 2026-06-15:** Router taxonomy reconciled (keep-and-relabel): broad
`weather/economics/sports/politics/unknown` categories retained for full
observation signal; soccer implemented as the enabled `subcategory` slice within
`sports`. Deterministic `ParserStatus` enum added.

- [x] Add deterministic parser status: `supported`, `unsupported`, `ambiguous`, `unsafe`.
- [x] Recognize soccer as the enabled slice within broad sports.
- [ ] Add weather contract parser for location/date/threshold.
- [ ] Add economics contract parser for release type/date/threshold.
- [ ] Add soccer contract parser for teams/market type/date.
- [x] Record observed markets (including unsupported) instead of ignoring them.

Exit criteria:

- Real market list shows category and parser status.
- Unsupported markets have clear skip reasons.
- Only supported parsed contracts can enter research.

## Phase 3: Real Source-Backed Research

**Goal:** Fetch real category research and persist source/cache metadata.

- [ ] Weather: use NWS-backed research for supported weather contracts.
- [ ] Economics: use FRED/BLS/Fed-backed research for supported macro contracts.
- [ ] Soccer: add a `SoccerResearchFetcher` backed by a reliable fixture/team/result source.
- [ ] Use `SourceCache` for all external source calls.
- [ ] Attach source health, freshness, cache hit/miss, and provenance to each research snapshot.
- [ ] Skip decisions when required research is stale, missing, or unparsable.

Exit criteria:

- Every supported real market has either usable research or a deterministic research skip.
- UI can show real source health and cache status.

## Phase 4: Real-Data Paper Decision Loop

**Goal:** Produce auditable TRADE/SKIP decisions from real market snapshots and real research.

- [ ] Add a controlled scanner loop that runs in paper mode only.
- [ ] Add scan limits for max markets per run and max paper decisions per run.
- [ ] Use deterministic gate tracing for all supported categories.
- [ ] Record decisions in `PaperStore`.
- [ ] Record skips in `PaperStore`.
- [ ] Record paper fills only after all gates pass.
- [ ] Keep manual trial controls separate from real-data paper decisions.

Exit criteria:

- A scan can process real markets and persist TRADE/SKIP results.
- Paper fills are durable and visible in the UI.
- Live trading remains disabled.

## Phase 5: Outcome Labeling And PnL

**Goal:** Settle paper trades against real market outcomes.

- [ ] Add outcome polling for resolved Kalshi markets.
- [ ] Link outcomes to paper fills.
- [ ] Handle canceled/unresolved markets without false PnL.
- [ ] Calculate realized PnL from stored fill price, side, size, and fees.
- [ ] Update performance UI to distinguish realized PnL from open exposure.

Exit criteria:

- Settled markets update paper PnL.
- Open exposure decreases as outcomes resolve.
- Duplicate settlement polling is idempotent.

## Phase 6: Training Dataset Builder

**Goal:** Convert observed markets into category-specific training rows.

- [ ] Add table/schema for market snapshot features.
- [ ] Add table/schema for research features.
- [ ] Add table/schema for model predictions.
- [ ] Add table/schema for settled labels.
- [ ] Include skipped and traded markets.
- [ ] Add export command for category-specific datasets.
- [ ] Enforce timestamp-safe feature creation.

Exit criteria:

- We can export weather, economics, and soccer datasets.
- Each row has features available at prediction time and outcome labels only after settlement.

## Phase 7: Baseline Category Models

**Goal:** Add simple category-specific models before heavier ML.

- [ ] Add `WeatherProbabilityModel` baseline.
- [ ] Add `EconomicsProbabilityModel` baseline.
- [ ] Add `SoccerProbabilityModel` baseline.
- [ ] Add model version and feature schema version to predictions.
- [ ] Compare predictions against market-implied probability.
- [ ] Store predictions before outcomes are known.

Exit criteria:

- Each category has a baseline probability model.
- Model predictions are durable and auditable.
- Decision engine still controls all trades.

## Phase 8: Backtesting And Evaluation

**Goal:** Prove model quality before using models in paper trading.

- [ ] Add time-split train/test evaluation.
- [ ] Add Brier score, log loss, and calibration reports.
- [ ] Add paper-trading ROI simulation after spread/fees.
- [ ] Add closing-line value where available.
- [ ] Add category-specific performance reports.

Exit criteria:

- Models are evaluated out of sample.
- Leakage checks are documented.
- Weak models remain observation-only.

## Phase 9: Model-Assisted Paper Mode

**Goal:** Use category model probabilities in paper mode while retaining strict risk gates.

- [ ] Route supported markets to the correct category model.
- [ ] Store model prediction with each decision.
- [ ] Trade only when model edge clears all gates.
- [ ] Compare model-assisted paper performance against baseline decisions.
- [ ] Add UI model-version and category-performance visibility.

Exit criteria:

- Model-assisted paper trading runs without live execution.
- Performance can be reviewed by category and model version.

## Phase 10: Live Readiness Gate

**Goal:** Define but do not enable live trading until all safety and performance gates pass.

- [ ] Verify paper/live parity on order payload construction.
- [ ] Verify kill switch behavior.
- [ ] Verify max order size and daily loss caps.
- [ ] Verify position reconciliation design.
- [ ] Verify order cancellation/retry handling.
- [ ] Require explicit operator approval before live mode.

Exit criteria:

- Live trading remains disabled until the operator explicitly enables it.
- The system has a documented evidence pack for paper performance, safety, and operational readiness.

## Standing Rules

- Do not enable live trading during these phases.
- Do not let sports/soccer bypass source, parser, or risk gates.
- Do not train on post-outcome leaked data.
- Do not judge profitability from small samples.
- Prefer skips over low-quality trades.
- Commit each completed phase locally before moving to the next when Git is available.
