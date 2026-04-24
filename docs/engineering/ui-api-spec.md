# UI Read-Only API Specification

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Purpose
Define stable dashboard and paper-only trial API contracts used by the React dashboard.

## Global API Rules
- Base paths: `/api/ui` (read-only dashboard) and `/api/trial` (paper-only controls)
- Allowed methods:
  - `/api/ui/*`: `GET` only
  - `/api/trial/*`: `GET`, `POST` (paper-only)
- Content type: `application/json`
- Every response includes:
  - `timestamp` (ISO8601 UTC)
  - `freshness_seconds` (integer)
  - `source` (artifact/service origin)
- Typed error envelope:
  - `ok` (`false`)
  - `error_code`
  - `message`
  - `timestamp`
  - `trace_id`
  - `details` (optional)

## Endpoints

### `GET /api/ui/health`
- Returns system heartbeat and service status.
- Response fields:
  - `mode` (`paper` or `live`)
  - `heartbeat_status`
  - `last_heartbeat_at`
  - `providers` (kalshi, nws, search status)
  - `stale_data_alerts` (list)

### `GET /api/ui/markets`
- Returns tracked market snapshots.
- Query params:
  - `limit` (optional, default 50)
- Response fields:
  - `markets` array of:
    - `market_id`
    - `yes_bid`, `yes_ask`, `no_bid`, `no_ask`
    - `volume`
    - `snapshot_timestamp`
    - `spread`

### `GET /api/ui/decisions`
- Returns decision feed for recent evaluations.
- Query params:
  - `limit` (optional, default 100)
  - `market_id` (optional)
- Response fields:
  - `decisions` array of:
    - `decision_id`
    - `market_id`
    - `mixed_probability`
    - `market_implied_probability`
    - `edge`
    - `risk_gate_result`
    - `decision`
    - `trace_id`
    - `decision_timestamp`

### `GET /api/ui/metrics/replay`
- Returns replay quality metrics.
- Response fields:
  - `brier_score`
  - `brier_threshold`
  - `brier_pass`
  - `calibration_summary`
  - `last_replay_at`

### `GET /api/ui/metrics/paper`
- Returns paper-trading operational metrics.
- Response fields:
  - `paper_pnl`
  - `wins`
  - `losses`
  - `total_trades`
  - `risk_gate_failures`
  - `last_trade_at`

### `GET /api/ui/audit`
- Returns recent audit and error events.
- Query params:
  - `trace_id` (optional)
  - `level` (optional)
  - `limit` (optional, default 100)
- Response fields:
  - `events` array of:
    - `trace_id`
    - `event_type`
    - `actor`
    - `status`
    - `message`
    - `level`
    - `event_timestamp`

### `GET /api/ui/inference-health`
- Returns inference runtime diagnostics for operator visibility.
- Response fields:
  - `inference.base_url`
  - `inference.brain_model`
  - `inference.hands_model`
  - `inference.total_calls`
  - `inference.fallback_calls`
  - `inference.fallback_rate`
  - `inference.last_source`
  - `inference.last_fallback_reason`

### `GET /api/ui/trial-decision-trace`
- Returns recent decision/risk trace entries for trial actions.
- Query params:
  - `limit` (optional, default 20)
- Response fields:
  - `traces` array of:
    - `trace_id`
    - `market_id`
    - `decision`
    - `risk_gate_result`
    - `edge`
    - `expected_value`
    - `inferred_probability`
    - `implied_probability`
    - `inference_source`
    - `inference_fallback_reason`
    - `inference_latency_ms`
    - `model`
    - `gate_context` (`min_confidence`, `max_position_usd`, `daily_loss_limit_usd`, `gap_threshold_pct`)
    - `decision_timestamp`

### `POST /api/trial/bets/manual`
- Places a paper-only manual bet after DecisionEngine risk-gate evaluation.
- Request fields:
  - `market_id`
  - `side` (`YES` or `NO`)
  - `contracts`
- Success response:
  - `ok` (`true`)
  - `bet`
  - `balance_usd`
- Failure response:
  - typed error envelope (includes optional `details.trace` with gate context)

### `POST /api/trial/bets/auto`
- Places a paper-only auto bet using inference plus DecisionEngine gating.
- Request fields:
  - `market_id`
  - `contracts`
- Success/failure schema matches manual bet endpoint.

### `POST /api/trial/scenarios/run`
- Executes bounded pre-key scenario controls for operator simulation.
- Guardrails:
  - max 20 scenarios per run
  - paper-only semantics
  - `dry_run=true` performs non-mutating simulation path
- Request fields:
  - `dry_run` (default `true`)
  - `scenarios[]` (`market_id`, `mode`, optional `side`, `contracts`)
- Response fields:
  - `dry_run`
  - `summary.total`
  - `summary.pass`
  - `summary.fail`
  - `summary.no_trade`
  - `summary.fallback_count`
  - `summary.results`

## Security and Safety Constraints
- Non-GET methods on `/api/ui/*` MUST return `405 Method Not Allowed`.
- `/api/ui/*` endpoints MUST not mutate decision, execution, or risk state.
- Live execution data may be displayed, but no endpoint may trigger orders.
- Trial mutation endpoints are explicitly paper-only and must never route to live execution.

## Reliability Constraints
- APIs should degrade gracefully with empty-data defaults.
- Missing artifacts should return `200` with empty arrays and warnings where safe.
- Parsing failures should return typed error responses without stack traces.
