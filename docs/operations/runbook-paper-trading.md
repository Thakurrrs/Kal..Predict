# Paper Trading Runbook

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## Preconditions
- Required services available
- Configuration validated
- Risk caps loaded

## Startup Procedure
1. Validate config and secrets.
2. Start data ingestion services.
3. Start forecasting and decision pipeline in paper mode.
4. Verify heartbeat and audit logs.

## Monitoring
- Key health indicators: ingestion freshness, forecast generation rate, risk gate pass/fail counts, paper fill simulation status.
- Alert thresholds: stale data beyond limit, repeated provider failures, abnormal decision spikes, any risk-gate bypass attempt.
- Dashboard links: to be defined when observability stack is selected.

## Shutdown and Recovery
- Safe shutdown steps:
  1. Stop UI and API processes gracefully.
  2. Confirm latest heartbeat and replay artifacts are flushed to disk.
  3. Snapshot current paper state files into a dated backup folder.
- Restart steps:
  1. Start API in paper mode and confirm `/api/ui/health` is reachable.
  2. Start UI and verify trial endpoints return data.
  3. Confirm inference health endpoint and fallback counters are visible.
- State recovery steps:
  1. Restore the latest known-good backup for:
     - `data/replay_results.json`
     - `data/heartbeat/state.json`
     - `logs/kal_predict.log` (optional for analysis)
  2. Restart API and run smoke probes:
     - `GET /api/ui/health`
     - `GET /api/ui/inference-health`
     - `GET /api/trial/markets?limit=1`
  3. If recovery probe fails, switch to observation-only mode and create incident record.

## Mandatory Safety Steps
- If uncertainty exists, stop automation and switch to observation-only mode.
- Never transition from paper to live mode through runbook shortcuts.
- Record every abnormal event in incident log with trace ID references.
