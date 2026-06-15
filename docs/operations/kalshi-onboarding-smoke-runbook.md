# Kalshi Credential Onboarding Smoke Runbook

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 2.0.0
- Last Updated: 2026-06-15
- Status: Approved

## Purpose
Define the exact smoke-test sequence to run once Kalshi credentials are
configured, starting with the demo environment before touching production.
The system stays paper-only throughout.

## Credential setup (one-time)

### Demo environment (do this first)
1. Create a demo account at https://demo.kalshi.co
2. Generate API keys: Settings → API Keys → Create New API Key
3. Copy `.env.template` to `.env` and fill in:

```
KALSHI_API_KEY_ID=<demo key id>
KALSHI_PRIVATE_KEY_PEM=<demo private key — full PEM block or single line with \n>
KALSHI_BASE_URL=https://external-api.demo.kalshi.co
EXECUTION_MODE=paper
```

### Production environment (later, after demo passes)
Same process on kalshi.com. Change `KALSHI_BASE_URL` to:
`https://external-api.kalshi.com`

## Step 0 — Credential preflight
```bash
python scripts/kalshi_credential_preflight.py
```
Expected: `OK ... private_key_source=inline`

## Step 1 — Stage 1 smoke (no backend needed)
```bash
python scripts/demo_smoke.py
```
Expected:
- Demo host confirmed
- Market list returns real markets
- source=kalshi_read_only

## Step 2 — Stage 2 smoke (with backend)
In one terminal:
```bash
uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030 --reload
```
In a second terminal:
```bash
python scripts/demo_smoke.py --with-backend
```
Expected:
- provider_status=credentialed
- EXECUTION_MODE=paper
- source=kalshi_read_only in /api/ui/markets

## Step 3 — Run observation scanner
```bash
python -c "
import asyncio
from kal_predict.config import load_config
from kal_predict.adapters.market import KalshiMarketDataProvider
from kal_predict.storage.paper_store import PaperStore
from kal_predict.pipeline.observation_scanner import ObservationScanner

config = load_config()
pem = config.kalshi.load_private_key()
provider = KalshiMarketDataProvider(
    api_key_id=str(config.kalshi.api_key_id),
    private_key_pem=pem,
    base_url=config.kalshi.base_url,
)
store = PaperStore(config.paper_data.database_path)
store.initialize()
scanner = ObservationScanner(provider, store)
print(asyncio.run(scanner.scan(max_markets=100)))
"
```

## Step 4 — Throughput report
```bash
python scripts/observation_throughput_report.py
```

## Step 5 — Capture evidence
Record and append to `docs/quality/pre-key-phase2-evidence-pack.md`:
- Timestamp
- Branch + commit hash (`git log --oneline -1`)
- Output of smoke test (copy/paste)
- Output of throughput report

## Failure policy
- Any FAIL in the smoke test means stop — do not proceed.
- Fix the issue, rerun the full sequence from Step 0.
- No live-write enablement at any point in this runbook.
