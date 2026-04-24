# Current Status (Session Handoff)

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-24
- Status: Approved

## Snapshot
- Current phase: **V1 pre-live readiness** (pre-key paper mode complete baseline).
- V1 completion definition: **live Kalshi-integrated automated prediction** (not yet complete).
- Active market scope: **weather-only** in current implementation.
- Forward readiness: interfaces and docs should remain category-ready so macro/events can be onboarded in a later phase without major refactor.
- Runtime baseline:
  - Backend API: `http://127.0.0.1:8030`
  - UI: `http://127.0.0.1:3040` (proxy via `API_PROXY_TARGET`)
  - Trial page: `http://127.0.0.1:3040/trial`

## Completed Recently
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
1. Continue Kalshi-key-dependent onboarding once credentials are available:
   - authenticated read smoke tests
   - paper parity validation on real reads
   - keep `EXECUTION_MODE=paper` until Gate F approval.

## Quick Resume Commands
```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
source venv/bin/activate
uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030 --reload
```

```bash
API_PROXY_TARGET="http://127.0.0.1:8030" WATCHPACK_POLLING=true \
  npm --prefix "/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/ui" run dev -- \
  --hostname 127.0.0.1 --port 3040
```
