# Audit-Proof Paper Trading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make paper trading auditable and replayable by adding source caching, durable SQLite storage, conservative sizing, deterministic gate traces, and outcome/PnL accounting before enabling the autonomous loop.

**Architecture:** Add a persistent source cache and paper store in SQLite, then layer sizing and full gate traces into decisioning. Outcome handling and PnL use stored fills rather than transient in-memory state. The autonomous loop remains disabled until these foundations pass tests.

**Tech Stack:** Python 3.11, Pydantic v2, SQLite standard library, pytest, existing Kal..Predict models and adapters.

---

## File Structure

Create:

- `src/kal_predict/research/source_cache.py`  
  Persistent cache for source responses with deterministic keys, TTL handling, and source health metadata.

- `src/kal_predict/storage/__init__.py`  
  Storage package marker.

- `src/kal_predict/storage/paper_store.py`  
  SQLite table creation, idempotent inserts, transactions, fills, outcomes, skips, and performance queries.

- `src/kal_predict/core/sizing.py`  
  Conservative paper sizing with fractional-Kelly input, whole-contract rounding, and exposure caps.

- `tests/research/test_source_cache.py`  
  Source cache hit, miss, expiry, key isolation, and failure behavior.

- `tests/storage/test_paper_store.py`  
  Table creation, idempotency, transaction rollback, fill/outcome constraints, and PnL persistence tests.

- `tests/core/test_sizing.py`  
  Sizing guardrail tests.

Modify:

- `src/kal_predict/config.py`  
  Add paper store path, cache TTL defaults, bankroll, sizing, and exposure cap config.

- `src/kal_predict/models.py`  
  Add small Pydantic models for cache results, sizing results, paper fills, and outcomes if tests show the model contracts should be shared.

- `src/kal_predict/core/decision.py`  
  Add complete deterministic gate trace contract.

- `tests/core/test_decision_engine.py`  
  Add gate-by-gate skip reason tests.

- `docs/superpowers/plans/2026-06-08-profit-first-autonomous-paper-trading.md`  
  Mark completed source cache/store/sizing/gate/outcome tasks as they land.

---

## Task 1: Persistent Source Cache

**Files:**
- Create: `src/kal_predict/research/source_cache.py`
- Test: `tests/research/test_source_cache.py`
- Modify: `src/kal_predict/config.py`

- [ ] **Step 1: Write failing cache miss test**

Add:

```python
import pytest

from kal_predict.research.source_cache import SourceCache


@pytest.mark.asyncio
async def test_source_cache_fetches_and_persists_on_miss(tmp_path):
    cache = SourceCache(tmp_path / "paper.db", now=lambda: "2026-06-09T12:00:00+00:00")
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return {"temperature": 72}

    result = await cache.get_or_fetch(
        source="NWS",
        cache_key="points:nyc",
        ttl_seconds=3600,
        fetch=fetch,
    )

    assert result.payload == {"temperature": 72}
    assert result.cache_hit is False
    assert result.source_health.source == "NWS"
    assert result.source_health.status == "ok"
    assert calls == 1
```

- [ ] **Step 2: Run miss test red**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest tests/research/test_source_cache.py::test_source_cache_fetches_and_persists_on_miss -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Expected: import failure for `kal_predict.research.source_cache`.

- [ ] **Step 3: Implement minimal cache miss path**

Create `SourceCacheResult` dataclass and `SourceCache.get_or_fetch()`. Use SQLite standard library. Store `source`, `cache_key`, JSON payload, `retrieved_at`, and `expires_at`. Create table on initialization.

- [ ] **Step 4: Run miss test green**

Run the same focused test. Expected: pass.

- [ ] **Step 5: Add cache hit test**

Add:

```python
@pytest.mark.asyncio
async def test_source_cache_returns_cached_payload_before_expiry(tmp_path):
    cache = SourceCache(tmp_path / "paper.db", now=lambda: "2026-06-09T12:00:00+00:00")
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        return {"value": calls}

    first = await cache.get_or_fetch("FRED", "series:CPIAUCSL", 3600, fetch)
    second = await cache.get_or_fetch("FRED", "series:CPIAUCSL", 3600, fetch)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.payload == {"value": 1}
    assert calls == 1
```

- [ ] **Step 6: Implement cache hit path**

Read existing row by `(source, cache_key)`. Return hit only when `expires_at > now`.

- [ ] **Step 7: Add expiry and key isolation tests**

Add one test where `now` advances beyond `expires_at` and fetch is called again. Add one test where two different keys do not share payload.

- [ ] **Step 8: Add config**

In `config.py`, add:

```python
class PaperDataConfig(BaseSettings):
    database_path: str = Field(default="data/paper_trading.db")
    default_source_cache_ttl_seconds: int = Field(default=900)
    nws_cache_ttl_seconds: int = Field(default=1800)
    fred_cache_ttl_seconds: int = Field(default=21600)

    model_config = ConfigDict(env_prefix="PAPER_DATA_")
```

Add `paper_data: PaperDataConfig` to `AppConfig`.

- [ ] **Step 9: Verify and commit**

Run:

```powershell
.\.venv\Scripts\ruff.exe check src/kal_predict/config.py src/kal_predict/research/source_cache.py tests/research/test_source_cache.py
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest tests/research/test_source_cache.py tests/test_config.py -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Commit:

```powershell
git add src/kal_predict/config.py src/kal_predict/research/source_cache.py tests/research/test_source_cache.py
git commit -m "feat: add persistent source cache"
```

---

## Task 2: SQLite Paper Store Schema And Idempotency

**Files:**
- Create: `src/kal_predict/storage/__init__.py`
- Create: `src/kal_predict/storage/paper_store.py`
- Test: `tests/storage/test_paper_store.py`

- [ ] **Step 1: Write failing table creation test**

```python
from kal_predict.storage.paper_store import PaperStore


def test_paper_store_creates_required_tables(tmp_path):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()

    tables = store.table_names()

    assert "research_snapshots" in tables
    assert "decisions" in tables
    assert "paper_fills" in tables
    assert "outcomes" in tables
    assert "market_skips" in tables
    assert "performance_daily" in tables
    assert "source_cache" in tables
```

- [ ] **Step 2: Run table test red**

Expected: import failure for `kal_predict.storage.paper_store`.

- [ ] **Step 3: Implement schema creation**

Create `PaperStore.initialize()` with `CREATE TABLE IF NOT EXISTS` statements and indexes:

- `decisions(trace_id)`
- `decisions(market_id)`
- `paper_fills(market_id)`
- `paper_fills(decision_id)`
- `outcomes(market_id)`
- `market_skips(market_id, reason)`

- [ ] **Step 4: Add idempotent decision insert test**

Use a `Decision` model instance. Insert twice. Assert only one row exists or the second insert returns `"ignored"` deterministically.

- [ ] **Step 5: Implement `record_decision()`**

Serialize the Pydantic model with `model_dump_json()`. Enforce `decision_id UNIQUE`.

- [ ] **Step 6: Add fill idempotency test**

Insert one fill for a decision, insert same fill again, assert no double-count. Insert a different fill for the same decision and assert it is rejected.

- [ ] **Step 7: Implement `record_fill()`**

Use `decision_id UNIQUE` in `paper_fills` until partial fills are explicitly supported.

- [ ] **Step 8: Add transaction rollback test**

Create a method `record_decision_and_fill(decision, fill)` where an invalid fill causes rollback. Assert neither record is stored.

- [ ] **Step 9: Implement transaction wrapper**

Use `with connection:` so SQLite commits atomically or rolls back on exception.

- [ ] **Step 10: Verify and commit**

Run:

```powershell
.\.venv\Scripts\ruff.exe check src/kal_predict/storage/paper_store.py tests/storage/test_paper_store.py
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest tests/storage/test_paper_store.py -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Commit:

```powershell
git add src/kal_predict/storage tests/storage/test_paper_store.py
git commit -m "feat: add durable paper store schema"
```

---

## Task 3: Conservative Paper Sizing

**Files:**
- Create: `src/kal_predict/core/sizing.py`
- Test: `tests/core/test_sizing.py`
- Modify: `src/kal_predict/config.py`

- [ ] **Step 1: Add sizing config**

Add:

```python
class PaperSizingConfig(BaseSettings):
    bankroll_usd: float = Field(default=10000.0)
    kelly_fraction: float = Field(default=0.10, ge=0.0, le=1.0)
    min_contracts: int = Field(default=1, ge=1)
    max_dollars_per_trade: float = Field(default=100.0)
    max_daily_risk_usd: float = Field(default=300.0)
    max_category_exposure_usd: float = Field(default=500.0)
    max_series_exposure_usd: float = Field(default=250.0)
    longshot_price_threshold: float = Field(default=0.10)
    max_longshot_dollars: float = Field(default=25.0)

    model_config = ConfigDict(env_prefix="PAPER_SIZING_")
```

Add `paper_sizing: PaperSizingConfig` to `AppConfig`.

- [ ] **Step 2: Write failing zero-edge test**

```python
from kal_predict.config import PaperSizingConfig
from kal_predict.core.sizing import PaperSizer


def test_sizer_returns_zero_when_net_edge_not_positive():
    result = PaperSizer(PaperSizingConfig()).size_trade(
        price=0.50,
        net_edge=0.0,
        daily_risk_used=0.0,
        category_exposure=0.0,
        series_exposure=0.0,
    )

    assert result.contracts == 0
    assert "net_edge_not_positive" in result.failed_caps
```

- [ ] **Step 3: Implement minimal `PaperSizer`**

Create `SizingResult` dataclass with `contracts`, `notional_usd`, and `failed_caps`.

- [ ] **Step 4: Add invalid price and rounding tests**

Test `price=0`, `price=1`, and a valid price where notional rounds down to whole contracts.

- [ ] **Step 5: Add cap tests**

Test max dollars per trade, daily risk cap, category exposure cap, series exposure cap, and long-shot cap.

- [ ] **Step 6: Implement caps**

Apply caps before returning. If final contracts are below `min_contracts`, return zero with `below_min_contracts`.

- [ ] **Step 7: Verify and commit**

Run focused sizing tests and config tests, then commit:

```powershell
git add src/kal_predict/config.py src/kal_predict/core/sizing.py tests/core/test_sizing.py
git commit -m "feat: add conservative paper sizing"
```

---

## Task 4: Full Deterministic Gate Trace

**Files:**
- Modify: `src/kal_predict/core/decision.py`
- Test: `tests/core/test_decision_engine.py`

- [ ] **Step 1: Write failing gate trace test**

Add a test where research is unusable and assert:

```python
assert decision.risk_gate_result == "FAIL"
assert decision.skip_reason == "research_unusable"
assert decision.gate_results["research_usable"] == "FAIL"
```

- [ ] **Step 2: Add decision input helper**

Add a new method rather than overloading legacy `evaluate_trade()` too much:

```python
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
) -> Decision:
```

- [ ] **Step 3: Implement first failed gate behavior**

Record every gate in order. The first failure becomes `skip_reason`.

- [ ] **Step 4: Add one independent test per gate**

Use parametrized cases for the 18 gates from the design spec. Each case should assert the expected `skip_reason`.

- [ ] **Step 5: Preserve legacy tests**

Existing `evaluate_trade()` tests must continue passing. New gate tracing lives in `evaluate_paper_decision()` until the autonomous loop wiring uses it.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest tests/core/test_decision_engine.py -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Commit:

```powershell
git add src/kal_predict/core/decision.py tests/core/test_decision_engine.py
git commit -m "feat: add deterministic paper decision gates"
```

---

## Task 5: Paper Outcomes And PnL

**Files:**
- Modify: `src/kal_predict/storage/paper_store.py`
- Test: `tests/storage/test_paper_store.py`

- [ ] **Step 1: Write YES win/loss tests**

Insert a YES fill at `0.40`, settle won and lost. Assert:

- win net PnL is `(1 - 0.40) * contracts - fees`
- loss net PnL is `-(0.40 * contracts) - fees`

- [ ] **Step 2: Implement outcome calculation**

Add `record_outcome(fill_id, outcome)` and `calculate_fill_pnl(fill, outcome)`.

- [ ] **Step 3: Add NO win/loss tests**

Use same formula because buying NO pays like a side contract:

- winning NO: `(1 - fill_price) * contracts - fees`
- losing NO: `-(fill_price * contracts) - fees`

- [ ] **Step 4: Add cancellation and unresolved tests**

Canceled markets should not count as wins or losses. Unresolved fills remain exposure, not realized PnL.

- [ ] **Step 5: Add duplicate settlement polling test**

Recording the same outcome twice must not double-count PnL.

- [ ] **Step 6: Verify and commit**

Run storage tests and full tests, then commit:

```powershell
git add src/kal_predict/storage/paper_store.py tests/storage/test_paper_store.py
git commit -m "feat: add paper outcome pnl accounting"
```

---

## Task 6: Integrate Cache Into Weather And Economics Fetchers

**Files:**
- Modify: `src/kal_predict/research/weather.py`
- Modify: `src/kal_predict/research/economics.py`
- Test: `tests/research/test_weather.py`
- Test: `tests/research/test_economics.py`
- Test: `tests/research/test_source_cache.py`

- [ ] **Step 1: Add fetcher cache-hit tests**

For weather and economics, inject a `SourceCache`. Call `fetch()` twice. Assert the HTTP mock is called once and the second snapshot still contains source health.

- [ ] **Step 2: Update fetcher constructors**

Add optional `source_cache: SourceCache | None = None` and TTL config arguments.

- [ ] **Step 3: Wrap NWS point/forecast and FRED observations calls**

Use cache keys:

- `NWS:points:{lat},{lon}`
- `NWS:forecast_hourly:{url}`
- `FRED:series_observations:{series_id}`

- [ ] **Step 4: Verify and commit**

Run research tests and commit:

```powershell
git add src/kal_predict/research tests/research
git commit -m "feat: cache weather and economics sources"
```

---

## Task 7: Full Verification And Plan Update

**Files:**
- Modify: `docs/superpowers/plans/2026-06-08-profit-first-autonomous-paper-trading.md`
- Modify: `docs/superpowers/plans/2026-06-09-audit-proof-paper-trading.md`

- [ ] **Step 1: Mark completed tasks**

Mark source cache, paper store, sizing, gate tracing, outcome accounting, and source-cache integration checkboxes as completed only for verified work.

- [ ] **Step 2: Run full verification**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest-tmp
```

Expected: all tests pass.

- [ ] **Step 3: Commit plan updates**

```powershell
git add docs/superpowers/plans/2026-06-08-profit-first-autonomous-paper-trading.md docs/superpowers/plans/2026-06-09-audit-proof-paper-trading.md
git commit -m "docs: update audit-proof paper trading progress"
```

---

## Execution Notes

- Do not push to GitHub.
- Do not enable live trading.
- Do not wire the autonomous loop until the store, sizing, gates, and outcome accounting are complete and verified.
- Use elevated filesystem permissions for pytest/ruff/Git if the sandbox blocks repo-local temp/cache/index writes.
