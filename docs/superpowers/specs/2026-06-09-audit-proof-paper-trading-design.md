# Audit-Proof Paper Trading Design

## Goal

Build the next profit-first foundation for Kal..Predict: cache structured research sources, persist every paper-trading artifact, size paper trades conservatively, and calculate auditable paper PnL before any autonomous loop is allowed to place paper fills.

## Scope

This design covers the next development phase after the conservative weather/economics fetchers and executable-edge decision engine. It does not add live trading, does not expand categories, and does not optimize for trade volume. The system should prefer skipping over producing unauditable or weakly supported paper trades.

## Architecture

The next phase adds four bounded components:

1. `research/source_cache.py` stores source responses per scan/request with TTLs and deterministic cache keys.
2. `storage/paper_store.py` persists research snapshots, decisions, skips, paper fills, outcomes, and daily performance in SQLite.
3. `core/sizing.py` converts approved net edge into capped whole-contract paper sizes.
4. `core/decision.py` is extended so all profit-first gates write explicit pass/fail trace data.

The autonomous research loop remains out of scope until these pieces exist. This keeps paper trading replayable and prevents untrusted paper PnL claims.

## Source Cache

Source caching should be category-agnostic. A fetcher asks the cache for a response using:

- `source`: `NWS`, `FRED`, or future source name.
- `cache_key`: stable hashable string from endpoint, params, and normalized source inputs.
- `ttl_seconds`: source-specific freshness limit.
- `fetch`: async callable used only on cache miss or expired entry.

The cache returns a small result object:

- `payload`
- `cache_hit`
- `retrieved_at`
- `expires_at`
- `source_health`

Failures are not cached by default except short-lived timeout protection if needed later. Evidence sent to downstream code must still include source name, endpoint/URL, retrieval timestamp, and freshness.

## Durable Store

The paper store uses SQLite and must be restart-safe. It creates tables on startup and uses transactions for multi-record writes.

Tables:

- `research_snapshots`
- `decisions`
- `paper_fills`
- `outcomes`
- `market_skips`
- `performance_daily`
- `source_cache`

Idempotency is mandatory:

- Unique `research_snapshot_id`.
- Unique `decision_id`.
- One fill per decision unless a later explicit partial-fill feature is added.
- One outcome per fill.
- Skips keyed by scan, market, reason, and trace so repeated scans are auditable without double-counting fills.

The store must never delete audit records during normal operation.

## Sizing

Sizing starts conservative. It uses side ask price, net edge, and bankroll config to produce whole contracts.

Rules:

- Return zero when `net_edge <= 0`.
- Return zero when price is outside `(0, 1)`.
- Apply fractional Kelly only after conservative caps.
- Round down to whole contracts.
- Enforce max dollars per trade.
- Enforce daily paper risk.
- Enforce category exposure.
- Enforce same-series exposure.
- Enforce separate long-shot cap for very low ask prices.

Sizing should return both the chosen contract count and a structured list of failed caps.

## Deterministic Gates

Decision output must include `gate_results` with every gate checked in order. The first failed gate becomes `skip_reason`.

Gate order:

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

Every skip should be stored.

## Outcome And PnL

Outcome handling should be implemented after the store and sizing exist. PnL rules:

- Winning YES pays `1 - fill_price` per contract minus fees.
- Losing YES loses `fill_price` per contract plus fees.
- Winning NO pays `1 - fill_price` per contract minus fees.
- Losing NO loses `fill_price` per contract plus fees.
- Canceled markets do not count as wins or losses.
- Unresolved exposure is reported separately from realized PnL.

## Testing Strategy

Use TDD for each component.

Required test groups:

- Source cache hit/miss/expiry/key isolation.
- Store idempotency and transaction rollback.
- Sizing caps and whole-contract rounding.
- Gate-by-gate skip reasons.
- Outcome PnL for YES/NO win/loss/cancel/unresolved.

Run focused tests after each task and full pytest before each commit.

## Open Decisions

Default recommendations:

- Use SQLite in `data/paper_trading.db`.
- Keep source cache in the same SQLite database for persistence across restarts.
- Keep autonomous loop disabled until store, sizing, gates, and basic outcome accounting pass tests.
- Do not add live trading controls in this phase beyond preserving existing fail-closed defaults.
