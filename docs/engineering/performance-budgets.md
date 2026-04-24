# Performance Budgets (Pre-Key Phase 2)

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Purpose
Define measurable pre-key runtime budgets for API latency, inference responsiveness, and UI build/runtime behavior.

## Budgets

- API response budget (read-only endpoints):
  - `/api/ui/health`: p95 <= 250 ms
  - `/api/ui/inference-health`: p95 <= 300 ms
  - `/api/trial/markets?limit=1`: p95 <= 900 ms (includes local model inference)

- Inference budget:
  - Hands inference median <= 1200 ms
  - Fallback rate target <= 5% during normal local operation
  - Fallback reason must always be populated when `inference_source=fallback`

- UI quality budget:
  - `npm --prefix ui run test`: required pass
  - `npm --prefix ui run build`: required pass
  - No type/lint failures in Next.js build output

## Alerting thresholds (manual pre-key)
- API p95 > 2x budget for two consecutive checks
- Fallback rate > 20% in routine local runs
- Inference-health endpoint unavailable for > 1 check interval

## Verification commands
- `pytest -q`
- `npm --prefix ui run test`
- `npm --prefix ui run build`
- `curl -s http://127.0.0.1:8030/api/ui/health`
- `curl -s http://127.0.0.1:8030/api/ui/inference-health`
- `curl -s "http://127.0.0.1:8030/api/trial/markets?limit=1"`
