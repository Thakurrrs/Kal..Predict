# Pre-Key Phase 2 Evidence Pack

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 2.0.0
- Last Updated: 2026-06-15
- Status: Approved

## Scope
Evidence for Phase 2 work that is independent of Kalshi API credentials,
plus Phase 1 authenticated demo smoke evidence recorded 2026-06-15.

## Phase 1 — Authenticated Kalshi Demo Smoke (2026-06-15)

### Evidence
- Timestamp: 2026-06-15T19:42:34Z
- Branch: feature/repo-verification-dependency-audit
- Commit: 5daf494 feat: add demo smoke test script and update runbook (Phase 1)
- Environment: Kalshi demo (https://external-api.demo.kalshi.co)
- Credential mode: inline PEM (KALSHI_PRIVATE_KEY_PEM)
- Execution mode: paper

### Command
```
python scripts/demo_smoke.py
```

### Output
```
[✓] Credentials loaded
[✓] Demo host confirmed: https://external-api.demo.kalshi.co
[✓] Private key loaded
[✓] Provider constructed
[✓] Market list: 10 markets returned
[✓] source=kalshi_read_only: real Kalshi demo data confirmed
SMOKE PASSED — Phase 1 complete. Real demo data confirmed.
```

### Gate status
- source=kalshi_read_only: PASS
- provider_status=credentialed: PASS
- EXECUTION_MODE=paper: PASS
- Real markets returned: PASS (10 markets)
- Live order path enabled: NO (paper-only, fail-closed)

### Unblocked items
- phase2-kalshi-read: UNBLOCKED — real Kalshi read path confirmed working
- Observation scanner: ready to run against demo markets



## Command evidence

### Backend verification
- Command: `pytest -q`
- Result: pass
- Evidence: `176 passed in 3.96s`

### UI verification
- Command: `npm --prefix ui run test`
- Result: pass
- Evidence: `4 passed (4)`

### UI build verification
- Command: `npm --prefix ui run build`
- Result: pass
- Evidence: Next.js build succeeds and includes `/trial` route.

### Live probe verification
- Command: `curl -s http://127.0.0.1:8030/api/ui/health`
  - Result: pass
  - Evidence: returns health payload with inference runtime block.
- Command: `curl -s http://127.0.0.1:8030/api/ui/inference-health`
  - Result: pass
  - Evidence: returns model config and fallback counters.
- Command: `curl -s "http://127.0.0.1:8030/api/trial/markets?limit=1"`
  - Result: pass
  - Evidence: `inference_source` reported as `ollama`; model shown as configured hands model.
- Command: manual insufficient-balance probe:
  - `curl -s -X POST http://127.0.0.1:8030/api/trial/bets/manual ... contracts=1000`
  - Result: pass
  - Evidence: deterministic error envelope with `error_code`, `message`, `timestamp`, `trace_id`.

## Known limitations (pre-key)
- Real Kalshi authenticated read-path is blocked until credentials are available.
- Paper parity validation against real Kalshi reads is blocked until read-path onboarding is complete.
- Execution remains paper-only by design.

## Blocked-by-key section
- Blocked item: `phase2-kalshi-read`
  - Unblock trigger: valid `KALSHI_API_KEY_ID` + `KALSHI_PRIVATE_KEY_PATH`, then read-only smoke checks pass.
- Blocked item: `phase2-paper-parity`
  - Unblock trigger: real read-path available, then parity tests against live reads pass with fail-closed gates.
