# Profit-First Autonomous Paper Trading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous research and paper-trading system that scans Kalshi markets, researches supported categories, makes audited paper bets, and proves edge by net profit before any live execution is enabled.

**Architecture:** Keep live betting disabled while expanding the current mock/paper system into a measured research loop. The bot reads real Kalshi markets, classifies only supported categories, fetches deterministic evidence, asks the LLM for structured probability estimates, paper-executes only when deterministic gates pass, records every skipped and placed decision, and reports net PnL after fees/slippage by category. Live order submission remains out of scope until the paper system passes explicit profit and risk criteria.

**Tech Stack:** FastAPI, Pydantic v2, httpx, SQLite/aiosqlite, Ollama, pytest, existing structured logging, Next.js dashboard.

---

## Operating Principle

The success metric is not 70% correct outcomes. The primary metric is positive risk-adjusted net profit in paper mode after realistic fees, spread, and slippage. Secondary metrics are calibration, Brier score, max drawdown, trade count, category-level PnL, and skipped-market audit quality.

Live execution must remain fail-closed until all paper promotion gates pass:

- At least 200 resolved paper trades.
- Positive net PnL after fees and spread.
- Positive PnL in at least two supported categories, or one category with at least 60 resolved trades.
- Max drawdown below configured limit.
- No unaudited bet decisions.
- No live order code path enabled by default.

---

## File Structure

Create or modify these files:

```text
src/kal_predict/
  config.py                         # Add paper loop, data source, bankroll, and promotion-gate config.
  models.py                         # Expand MarketSnapshot, Decision, TradeIntent, and add research/outcome schemas.
  adapters/
    market.py                       # Implement real read-only Kalshi provider.
    execution.py                    # Fix paper execution pricing and keep live fail-closed.
  core/
    decision.py                     # Add side-aware edge, deterministic gates, and paper sizing.
    metrics.py                      # New: profit, drawdown, Brier, and calibration metrics.
  research/
    __init__.py                     # New package.
    router.py                       # New: classify markets into supported categories.
    base.py                         # New: category research interface.
    economics.py                    # New: FRED/BLS and release evidence.
    weather.py                      # New: NWS evidence wrapper.
    sports.py                       # New: structured sports evidence, initially soccer only if configured.
    politics.py                     # New: conservative news/poll evidence, paper-only.
  storage/
    __init__.py                     # New package.
    paper_store.py                  # New: SQLite store for decisions, fills, outcomes, skips.
  pipeline/
    research_loop.py                # New: scan, research, decide, paper-fill, record.
    orchestrator.py                 # Wire heartbeat to optional paper research loop.
  services/
    inference.py                    # Return structured probability, confidence, reasoning, parse status.
  api/
    routes.py                       # Add paper performance and decision audit endpoints.

tests/
  adapters/test_kalshi_readonly.py
  adapters/test_execution_adapters.py
  core/test_decision_engine.py
  core/test_metrics.py
  research/test_router.py
  research/test_fetchers.py
  storage/test_paper_store.py
  pipeline/test_research_loop.py
```

---

## Phase 0: Safety Baseline

### Task 0.1: Add Explicit Live-Trading Block

**Files:**
- Modify: `src/kal_predict/config.py`
- Modify: `src/kal_predict/adapters/execution.py`
- Test: `tests/adapters/test_execution_adapters.py`

- [x] Add config fields:
  - `EXECUTION_MODE=paper`
  - `LIVE_TRADING_ENABLED=false`
  - `PAPER_TRADING_ENABLED=true`
  - `PROMOTION_REQUIRED_RESOLVED_TRADES=200`

- [x] Update execution provider so any live intent returns `None` unless both `EXECUTION_MODE=live` and `LIVE_TRADING_ENABLED=true`.

- [x] Add test:

```python
async def test_live_trade_rejected_unless_explicitly_enabled(config):
    provider = PaperExecutionProvider()
    intent = TradeIntent(
        intent_id="intent-1",
        market_id="MARKET",
        side="YES",
        max_price=0.55,
        size=1,
        mode="live",
        created_at="2026-06-08T00:00:00+00:00",
        trace_id="trace-1",
    )
    fill = await provider.execute_trade(intent, market_bid=0.54, market_ask=0.56)
    assert fill is None
```

- [x] Run:

```powershell
python -m pytest tests/adapters/test_execution_adapters.py -q
```

Expected: all tests pass.

---

## Phase 1: Correct Market and Trade Contracts

### Task 1.1: Expand MarketSnapshot

**Files:**
- Modify: `src/kal_predict/models.py`
- Test: `tests/test_models.py`

- [x] Add fields required for autonomous research:
  - `ticker: str`
  - `title: str`
  - `category_hint: str | None`
  - `status: str`
  - `close_time: str | None`
  - `yes_mid: float | None`
  - `spread: float | None`
  - `liquidity: int | None`

- [x] Preserve backward compatibility by giving new fields defaults where safe.

- [x] Add tests that old fixture snapshots still validate and richer real-market snapshots validate.

### Task 1.2: Expand Decision and TradeIntent

**Files:**
- Modify: `src/kal_predict/models.py`
- Test: `tests/test_models.py`

- [x] Add decision fields:
  - `category`
  - `skip_reason`
  - `gate_results`
  - `confidence`
  - `signals_used`
  - `paper_expected_cost`

- [x] Add trade intent fields:
  - `price`
  - `size_dollars`
  - `edge`
  - `model_probability`
  - `market_price`
  - `category`
  - `research_snapshot_id`

- [x] Keep `size` as contract count because Kalshi orders use contract counts.

---

## Phase 2: Real Kalshi Read-Only Provider

### Task 2.1: Implement Authenticated Read-Only Client

**Files:**
- Modify: `src/kal_predict/adapters/market.py`
- Modify: `src/kal_predict/config.py`
- Test: `tests/adapters/test_kalshi_readonly.py`

- [x] Add config:
  - `KALSHI_BASE_URL=https://trading-api.kalshi.com`
  - `KALSHI_API_KEY_ID`
  - `KALSHI_PRIVATE_KEY_PATH`
  - `KALSHI_READ_TIMEOUT_SECONDS=20`

- [x] Implement request signing using current official Kalshi API key docs. Use RSA-PSS signing for authenticated endpoints.

- [x] Implement read-only methods:
  - `list_markets(status="open") -> list[MarketSnapshot]`
  - `get_market_snapshot(market_id: str) -> MarketSnapshot | None`
  - `get_orderbook(market_id: str) -> dict`

- [x] Do not implement order placement in this phase.

- [x] Add tests using mocked HTTP responses. Validate mapping of Kalshi cents to decimal probabilities.

### Task 2.2: Add Market Quality Filters

**Files:**
- Modify: `src/kal_predict/core/decision.py`
- Test: `tests/core/test_decision_engine.py`

- [x] Add deterministic pre-research filters:
  - skip closed markets
  - skip markets with missing bid/ask
  - skip markets with spread above configured threshold
  - skip markets below configured volume/liquidity
  - skip markets too close to close time unless explicitly allowed

- [x] Record every skip reason.

---

## Phase 3: Research System for Supported Categories

Phase 3 must be conservative. The bot may research many markets, but it only produces a usable research snapshot when the market can be mapped to a supported category, parsed into the required domain fields, and backed by structured evidence. Any uncertainty in classification, parsing, API freshness, or source reliability should become a skip reason, not a low-quality bet.

Hard requirements for every category fetcher:

- No fetcher may call the LLM to invent missing facts.
- Every external response must include source name, URL or endpoint, retrieved timestamp, and freshness age.
- Every fetcher must return `usable=false` with a deterministic skip reason when required fields are missing.
- Every fetcher must distinguish source failure from "evidence says no edge."
- Every fetcher must support cached responses so one scan cycle cannot exhaust free API limits.
- Every fetcher must cap evidence volume before sending to the LLM.
- Every fetcher must produce directional signals independently from the LLM.
- Every signal must include `direction`, `confidence`, `source`, and `rationale`.
- RSS/search/news evidence is context unless converted into a deterministic signal with a documented rule.
- A category can be enabled for research while disabled for paper trading.

### Task 3.1: Add Category Router

**Files:**
- Create: `src/kal_predict/research/router.py`
- Test: `tests/research/test_router.py`

- [x] Classify markets into:
  - `economics`
  - `weather`
  - `sports`
  - `politics`
  - `unknown`

- [x] Use deterministic keyword rules first.

- [ ] Use LLM fallback only when keyword rules return `unknown`.

- [ ] Cache classification by ticker.

- [x] Skip `unknown`; never force a bet on unknown markets.

- [x] Add ambiguity handling:
  - if keyword rules match multiple categories, return `unknown_ambiguous`
  - if LLM fallback returns anything outside the allowed enum, return `unknown_parse_failed`
  - if title is empty or generic, return `unknown_missing_title`
  - if category is supported but disabled by config, return `known_disabled`

- [x] Add tests for ambiguous examples:
  - "Will Trump attend the World Cup final?" must not be classified as pure sports.
  - "Will Fed cut rates before the election?" must not silently choose politics over economics.
  - "Will NYC get rain on election day?" must not silently choose weather over politics.

### Task 3.2: Add Research Fetcher Interface

**Files:**
- Create: `src/kal_predict/research/base.py`
- Test: `tests/research/test_fetchers.py`

- [x] Define `BaseResearchFetcher` with:
  - `category_name`
  - `min_edge_threshold`
  - `async fetch(market) -> ResearchSnapshot`
  - `signals(research_snapshot) -> list[Signal]`

- [x] Add Pydantic models for `ResearchSnapshot` and `Signal` in `models.py`.

- [x] Add required `ResearchSnapshot` fields:
  - `research_snapshot_id`
  - `market_id`
  - `category`
  - `usable`
  - `skip_reason`
  - `evidence_items`
  - `signals`
  - `source_health`
  - `retrieved_at`
  - `expires_at`

- [x] Add required `source_health` fields:
  - `source`
  - `status`
  - `latency_ms`
  - `freshness_seconds`
  - `error_code`

- [x] Add tests proving source outage returns `usable=false` and does not raise uncaught exceptions.

### Task 3.3: Implement Weather First

**Files:**
- Create: `src/kal_predict/research/weather.py`
- Test: `tests/research/test_fetchers.py`

- [x] Use NWS only.

- [x] Parse weather market title enough to identify location, metric, threshold, and deadline.

- [x] If parsing fails, return a research snapshot with `usable=false` and skip reason.

- [x] Produce structured signals from forecast probability, forecast uncertainty, and update recency.

- [x] Weather-specific skip cases:
  - [x] unsupported location
  - [x] unsupported weather metric
  - [x] threshold cannot be parsed
  - [x] event time cannot be mapped to forecast horizon
  - [x] NWS gridpoint lookup fails
  - [x] forecast is stale
  - [x] forecast horizon is beyond reliable range

- [x] Weather-specific tests:
  - [x] valid rain market creates usable research
  - [x] invalid threshold skips
  - [x] stale forecast skips
  - [x] NWS timeout skips with `source_failure_nws_timeout`

### Task 3.4: Implement Economics Second

**Files:**
- Create: `src/kal_predict/research/economics.py`
- Modify: `src/kal_predict/config.py`
- Test: `tests/research/test_fetchers.py`

- [x] Add `FRED_API_KEY` and optional BLS config.

- [x] Support a limited first set:
  - CPI
  - unemployment
  - Fed funds rate
  - GDP

- [x] Fetch official historical series.

- [x] Record release calendar, recent trend, prior value, and market threshold.

- [x] Skip economics markets that cannot be mapped to a supported series.

- [ ] Economics-specific skip cases:
  - unsupported economic indicator
  - market asks about a future revision not available from source
  - FRED/BLS series mapping is ambiguous
  - release date is unknown
  - latest official observation is stale relative to market question
  - market threshold cannot be parsed into a numeric comparison

- [x] Economics-specific tests:
  - [x] CPI threshold market maps to `CPIAUCSL`
  - [x] unemployment threshold market maps to `UNRATE`
  - [x] ambiguous "inflation" market without threshold skips
  - [x] missing `FRED_API_KEY` skips economics fetch without crashing

### Task 3.5: Add Sports and Politics as Paper-Only, Lower Priority

**Files:**
- Create: `src/kal_predict/research/sports.py`
- Create: `src/kal_predict/research/politics.py`
- Test: `tests/research/test_fetchers.py`

- [x] Sports first supports only competitions with a configured structured data source.

- [ ] Politics starts as observation-only unless all signals are structured and agreement is strong.

- [ ] RSS/search evidence is context, not a primary signal.

- [x] Sports-specific safety:
  - support only leagues configured in env
  - skip if team/entity parsing is ambiguous
  - skip if data source does not identify the exact match/event
  - skip if lineup/injury news is older than configured freshness threshold
  - cap API usage per scan and per day

- [ ] Politics-specific safety:
  - paper-only by default
  - require all deterministic signals to agree
  - skip markets more than configured days from resolution unless explicitly enabled
  - skip if evidence is only news sentiment
  - skip if market depends on legal interpretation or settlement ambiguity

---

## Phase 4: LLM Probability With Strict JSON

Phase 4 must treat the LLM as a reasoning summarizer, not as the source of truth. The LLM can estimate probability only from evidence that the research layer already fetched and structured. It cannot browse, fill missing data, override deterministic gates, or justify betting when evidence is unusable.

Hard requirements:

- Temperature must be zero for decision prompts.
- Prompts must include market title, settlement rule when available, current prices, close time, category, evidence, and explicit JSON schema.
- The parser must reject markdown, prose around JSON, missing fields, non-numeric probability, out-of-range probability, and invalid confidence values.
- If `parse_ok=false`, the default action is skip.
- If Ollama times out, the default action is skip.
- Fallback probabilities may be logged for diagnostics but must not trigger paper trades unless `ALLOW_FALLBACK_PAPER_DECISIONS=true`.
- Store raw LLM output for audit, capped to a safe length.
- Track parse failure rate by model and category.

### Task 4.1: Upgrade Inference Contract

**Files:**
- Modify: `src/kal_predict/services/inference.py`
- Modify: `src/kal_predict/models.py`
- Test: `tests/services/test_inference.py`

- [ ] Return:
  - `probability_yes`
  - `confidence`
  - `reasoning`
  - `key_factors`
  - `parse_ok`
  - `fallback_reason`

- [ ] Keep deterministic fallback when Ollama fails.

- [ ] If parsing fails, decision engine must skip rather than bet unless config explicitly allows fallback paper decisions.

- [ ] Add validation tests:
  - valid JSON passes
  - JSON wrapped in markdown fails
  - `"probability_yes": "high"` fails
  - probability above 1 fails
  - missing confidence fails
  - timeout produces `parse_ok=false`
  - fallback result is marked non-tradeable by default

### Task 4.2: Model Config Is Runtime-Tunable

**Files:**
- Modify: `src/kal_predict/config.py`
- Modify: `config/ollama.sh`
- Test: `tests/test_config.py`

- [ ] Add defaults:
  - `OLLAMA_BRAIN_MODEL=qwen3:30b`
  - `OLLAMA_HANDS_MODEL=qwen3:14b`

- [ ] Do not assume model upgrade creates edge.

- [ ] Add health metrics for latency, parse failure rate, and fallback rate by model.

- [ ] Add model readiness checks:
  - model is installed locally
  - simple JSON smoke prompt succeeds
  - p95 latency is below configured threshold
  - parse failure rate over smoke prompts is zero

- [ ] Add config to switch back to smaller models if Qwen3 latency is too high.

---

## Phase 5: Profit-First Decision Engine

Phase 5 is the highest-risk logic in the system. It decides whether simulated capital is put at risk, so every branch must be deterministic, explainable, and test-covered. The engine should prefer skipping over taking low-quality trades. It should optimize expected profit after spread, fees, and conservative slippage, not raw directional correctness.

Hard requirements:

- Use executable prices, not midpoint prices, for edge.
- YES edge uses the YES ask.
- NO edge uses the NO ask.
- Midpoint may be displayed but cannot be used to decide profit.
- Fees and slippage must reduce expected value before gates pass.
- No trade can pass without category, research snapshot, model result, and gate trace.
- Conflicting signals skip unless the category explicitly permits lower confluence.
- Correlated exposure must be capped by category and market series.
- A market already traded today must not be traded again unless position-increase rules are explicitly configured.
- The decision output must include the first failed gate and all gate results.

### Task 5.1: Add Side-Aware Edge and Pricing

**Files:**
- Modify: `src/kal_predict/core/decision.py`
- Test: `tests/core/test_decision_engine.py`

- [ ] Compute YES edge as `p_yes - yes_ask`.

- [ ] Compute NO edge as `(1 - p_yes) - no_ask`.

- [ ] Choose the side with better positive edge.

- [ ] Skip if neither side exceeds category threshold.

- [ ] Add fee/slippage-adjusted edge:
  - `raw_edge = model_side_probability - side_ask`
  - `fee_adjusted_edge = raw_edge - estimated_fee_probability_equivalent`
  - `net_edge = fee_adjusted_edge - slippage_buffer`

- [ ] Add tests:
  - YES selected when YES net edge is higher
  - NO selected when NO net edge is higher
  - no trade when midpoint edge exists but ask-price edge does not
  - no trade when fees erase edge
  - no trade when spread exceeds threshold

### Task 5.2: Add Paper Sizing

**Files:**
- Create: `src/kal_predict/core/sizing.py`
- Modify: `src/kal_predict/core/decision.py`
- Test: `tests/core/test_decision_engine.py`

- [ ] Use fractional Kelly only after applying conservative caps.

- [ ] Use actual side price:
  - YES uses `yes_ask`
  - NO uses `no_ask`

- [ ] Enforce:
  - min contract count
  - max dollars per trade
  - max daily paper risk
  - max exposure per category

- [ ] Add sizing guardrails:
  - return zero size when `net_edge <= 0`
  - return zero size when price is outside `(0, 1)`
  - round down to whole contracts
  - cap total open exposure
  - cap same-series exposure
  - cap daily newly opened exposure
  - cap long-shot markets separately because Kelly can overreact to uncertain tails

- [ ] Add tests for minimum bet, maximum bet, invalid prices, whole-contract rounding, and same-series cap.

### Task 5.3: Add Deterministic Gates

**Files:**
- Modify: `src/kal_predict/core/decision.py`
- Test: `tests/core/test_decision_engine.py`

- [ ] Gates:
  - category supported
  - research usable
  - LLM parse ok
  - minimum signal count
  - signal confluence
  - edge threshold
  - spread threshold
  - liquidity threshold
  - daily paper trade limit
  - exposure limit

- [ ] Every gate writes pass/fail and reason into `Decision.gate_results`.

- [ ] Add gate order:
  1. market open
  2. quotes present
  3. spread acceptable
  4. liquidity acceptable
  5. category supported
  6. category enabled for paper trading
  7. research usable
  8. source freshness acceptable
  9. LLM parse ok
  10. confidence acceptable
  11. signal count acceptable
  12. confluence acceptable
  13. net edge acceptable
  14. sizing above minimum
  15. daily trade count acceptable
  16. daily exposure acceptable
  17. category exposure acceptable
  18. series exposure acceptable

- [ ] Add tests where each gate fails independently and produces the expected skip reason.

---

## Phase 6: Durable Paper Trading Store

Phase 6 must make the system auditable and restart-safe. If the app crashes after researching, deciding, or paper-filling, the next run must be able to recover what happened and avoid duplicate trades. Paper PnL is only credible if decisions, fills, prices, outcomes, fees, and unresolved exposure are stored durably.

Hard requirements:

- Use SQLite transactions for multi-table writes.
- Store every scan, skip, decision, paper fill, and outcome.
- Enforce idempotency with stable keys: scan ID, market ID, decision ID, and trace ID.
- Prevent duplicate paper fills for the same decision.
- Store raw prices at decision time and fill time.
- Store both expected PnL at decision time and realized PnL after resolution.
- Store unresolved exposure separately from realized PnL.
- Store schema version for future migrations.
- Provide migration-safe table creation on startup.
- Never delete audit records during normal operation.

### Task 6.1: Add SQLite Paper Store

**Files:**
- Create: `src/kal_predict/storage/paper_store.py`
- Test: `tests/storage/test_paper_store.py`

- [ ] Create tables:
  - `research_snapshots`
  - `decisions`
  - `paper_fills`
  - `outcomes`
  - `market_skips`
  - `performance_daily`

- [ ] Store every scanned market, not only trades.

- [ ] Store trace IDs across research, decision, fill, and outcome.

- [ ] Add indexes:
  - `decisions(trace_id)`
  - `decisions(market_id)`
  - `paper_fills(market_id)`
  - `paper_fills(decision_id)`
  - `outcomes(market_id)`
  - `market_skips(market_id, reason)`

- [ ] Add idempotency constraints:
  - one research snapshot ID is unique
  - one decision ID is unique
  - one fill per decision unless explicitly marked as partial fill
  - one outcome per fill

- [ ] Add tests:
  - duplicate decision insert is rejected or ignored deterministically
  - duplicate fill for same decision cannot double-count PnL
  - crash-safe transaction rolls back partial writes

### Task 6.2: Record Paper Outcomes

**Files:**
- Modify: `src/kal_predict/storage/paper_store.py`
- Modify: `src/kal_predict/adapters/market.py`
- Test: `tests/storage/test_paper_store.py`

- [ ] Poll settlements/resolution data where available.

- [ ] Resolve paper fills into:
  - won/lost
  - gross PnL
  - fees
  - slippage estimate
  - net PnL

- [ ] Keep unresolved paper trades separate from resolved trades.

- [ ] Add outcome edge cases:
  - market canceled
  - market settles early
  - partial fills
  - unresolved beyond expected close time
  - settlement endpoint unavailable
  - ticker changed or market ID mapping changes

- [ ] Add PnL rules:
  - winning YES pays `1 - fill_price` per contract minus fees
  - losing YES loses `fill_price` per contract plus fees
  - winning NO pays `1 - fill_price` per contract minus fees
  - losing NO loses `fill_price` per contract plus fees
  - canceled markets should not count as wins or losses

- [ ] Add tests for YES win/loss, NO win/loss, cancellation, unresolved exposure, and duplicate settlement polling.

---

## Phase 7: Autonomous Paper Research Loop

### Task 7.1: Add Research Loop

**Files:**
- Create: `src/kal_predict/pipeline/research_loop.py`
- Modify: `src/kal_predict/pipeline/orchestrator.py`
- Test: `tests/pipeline/test_research_loop.py`

- [ ] Loop sequence:
  1. list open markets
  2. apply market quality filters
  3. classify category
  4. fetch research
  5. infer probability
  6. evaluate decision gates
  7. paper execute if approved
  8. store all artifacts

- [ ] Config:
  - `PAPER_RESEARCH_LOOP_ENABLED=false`
  - `PAPER_SCAN_INTERVAL_MINUTES=10`
  - `MAX_MARKETS_PER_SCAN=50`
  - `MAX_PAPER_TRADES_PER_SCAN=3`
  - `MAX_PAPER_TRADES_PER_DAY=10`

- [ ] Default remains disabled until credentials and data sources are configured.

### Task 7.2: Add Replay Mode

**Files:**
- Modify: `src/kal_predict/core/replay.py`
- Test: `tests/core/test_replay.py`

- [ ] Re-run stored decisions against historical/resolved data.

- [ ] Make replay deterministic using stored research snapshots and model outputs.

- [ ] Report whether profit came from real edge or unrealistic paper fill assumptions.

---

## Phase 8: Profit and Calibration Reporting

### Task 8.1: Add Metrics

**Files:**
- Create: `src/kal_predict/core/metrics.py`
- Test: `tests/core/test_metrics.py`

- [ ] Metrics:
  - net PnL
  - gross PnL
  - fees
  - win rate
  - average edge at bet time
  - average realized return
  - Brier score
  - max drawdown
  - profit factor
  - category-level PnL

### Task 8.2: Add API Endpoints

**Files:**
- Modify: `src/kal_predict/api/routes.py`
- Test: `tests/api/test_ui_api.py`

- [ ] Add:
  - `GET /api/paper/performance`
  - `GET /api/paper/decisions`
  - `GET /api/paper/skips`
  - `GET /api/paper/categories`

- [ ] Keep endpoints read-only.

### Task 8.3: Update Dashboard

**Files:**
- Modify: `ui/src/app/performance/page.tsx`
- Modify: `ui/src/app/decisions/page.tsx`
- Modify: `ui/src/app/markets/page.tsx`

- [ ] Show net PnL as the main score.

- [ ] Show unresolved exposure separately from realized PnL.

- [ ] Show skipped-market reasons so bad coverage is visible.

- [ ] Show model fallback/parse failure rate.

---

## Phase 9: Calibration, Not Overfitting

### Task 9.1: Start With Simple Calibration

**Files:**
- Create: `src/kal_predict/core/calibration.py`
- Test: `tests/core/test_calibration.py`

- [ ] Do not train LightGBM immediately.

- [ ] First implement reliability buckets:
  - 0.50-0.55
  - 0.55-0.60
  - 0.60-0.65
  - 0.65-0.70
  - 0.70+

- [ ] Report predicted probability vs realized frequency.

- [ ] Only enable probability adjustment after at least 200 resolved trades.

### Task 9.2: Add ML Calibrator Later

**Files:**
- Modify: `pyproject.toml`
- Create: `src/kal_predict/core/ml_calibrator.py`
- Test: `tests/core/test_calibration.py`

- [ ] Add LightGBM only after enough stored outcomes exist.

- [ ] Minimum for ML calibrator:
  - 300 resolved trades globally, or
  - 150 resolved trades in one category.

- [ ] Compare calibrator Brier score against raw probability before using it.

---

## Phase 10: Promotion Gate to Live

### Task 10.1: Add Promotion Report

**Files:**
- Create: `src/kal_predict/core/promotion.py`
- Test: `tests/core/test_promotion.py`

- [ ] Promotion criteria:
  - `resolved_trades >= 200`
  - `net_pnl > 0`
  - `max_drawdown <= configured_limit`
  - `brier_score <= configured_limit`
  - `parse_failure_rate <= configured_limit`
  - `all_trades_have_trace_id == true`
  - `all_live_controls_disabled_by_default == true`

- [ ] Produce a report explaining pass/fail per criterion.

### Task 10.2: Keep Live Execution as Separate Future Phase

**Files:**
- Modify: `docs/operations/runbook-paper-trading.md`
- Create: `docs/operations/live-promotion-checklist.md`

- [ ] Document that live trading is not part of the paper proving phase.

- [ ] Require manual review of the promotion report before live code is enabled.

- [ ] Require a tiny live pilot after promotion, with lower limits than paper mode.

---

## Revised Execution Order

1. Safety baseline and live block.
2. Market and trade schema corrections.
3. Kalshi read-only provider.
4. Paper execution realism fixes.
5. Weather research fetcher.
6. Economics research fetcher.
7. Profit-first decision gates and sizing.
8. Durable paper store.
9. Autonomous paper research loop.
10. Performance dashboard and promotion report.
11. Calibration after enough outcomes.
12. Live execution only in a separate, later plan.

---

## What This Plan Deliberately Avoids

- No autonomous live betting in the first build.
- No forced bets to increase activity.
- No 70% accuracy target.
- No blind trust in LLM probability.
- No immediate LightGBM with too little data.
- No category expansion before the first categories prove usable.
- No search/RSS as primary signal unless supported by structured evidence.
