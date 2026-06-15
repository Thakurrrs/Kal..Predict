# Current Status (Session Handoff)

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.1.0
- Last Updated: 2026-06-15
- Status: Approved

## Snapshot
- Current phase: **Real-data paper trading Phase 2** (category routing + observation scanner).
- V1 completion definition: **live Kalshi-integrated automated prediction** (not yet complete).
- Active market scope: **weather and economics paper-enabled; soccer observed as the enabled slice within broad `sports` (observation-only)**; current runtime still falls back to mock market data unless Kalshi credentials are configured.
- Forward readiness: interfaces and docs should remain category-ready so weather, economics, soccer, and later model-specific training paths can be onboarded without major refactor.
- Runtime baseline:
  - Backend API: `http://127.0.0.1:8030`
  - UI: `http://127.0.0.1:3040` (proxy via `API_PROXY_TARGET`)
  - Trial page: `http://127.0.0.1:3040/trial`

## Completed Recently
- Real-data paper trading roadmap, category-model architecture, and phased implementation plan added under `docs/superpowers`.
- Phase 1 provider selection added for `/api/ui/markets`:
  - uses `KalshiMarketDataProvider` when `KALSHI_API_KEY_ID` and private key path are configured
  - otherwise falls back to explicit `mock_market_provider`
  - exposes `source` and `provider_status` so mock data cannot be confused for real Kalshi data
- Market Prices UI now shows market source, provider status, status, close time, title/category hint, liquidity, spread, and volume.
- Durable paper metrics now read from `PaperStore` when paper fills exist, including open exposure.
- Trial actions wired through `DecisionEngine` with persisted gate outcomes.
- Typed error envelopes standardized across trial/UI endpoints.
- Scenario controls added (`POST /api/trial/scenarios/run`) with paper-only guardrails.
- Trial UI upgraded with:
  - user-friendly copy
  - richer trace fields
  - compact tooltip help for Brier/Edge/Confidence
- Docs synced to reflect `/api/ui/*` read-only + `/api/trial/*` paper-only controls.
- Gate status register added to distinguish implemented vs passed (`docs/governance/gate-status-register.md`).
- First-day credential onboarding smoke runbook added (`docs/operations/kalshi-onboarding-smoke-runbook.md`).
- Pre-key one-command readiness script added (`scripts/prekey_readiness.sh`).
- V2 post-weather onboarding plan documented (`docs/operations/v2-domain-onboarding-plan.md`).

## Open Items (Next Session)
1. Complete Phase 1 authenticated Kalshi read-only smoke once credentials are available:
   - authenticated read smoke tests
   - verify `/api/ui/markets` reports `source=kalshi_read_only` and `provider_status=credentialed`
   - verify the Market Prices UI renders real market IDs, titles, status, close time, spread, volume, and liquidity
   - keep `EXECUTION_MODE=paper` until Gate F approval.
2. Start Phase 2 category routing for weather, economics, and soccer after Phase 1 real-read smoke passes.

## Quick Resume Commands
```powershell
cd "F:\AI Stuff\AntiGravity\Projects\Claude\Kal..Predict"
.\.venv\Scripts\python.exe -m uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030 --reload
```

```powershell
$env:API_PROXY_TARGET="http://127.0.0.1:8030"
$env:WATCHPACK_POLLING="true"
npm.cmd --prefix ui --cache "F:\AI Stuff\AntiGravity\Projects\Claude\Kal..Predict\.npm-cache" run dev -- --hostname 127.0.0.1 --port 3040
```
