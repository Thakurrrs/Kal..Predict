# Development Setup

## Prerequisites

- Python 3.9+
- Node.js 20+ and npm (required for `ui/`)
- Ollama (installed and running)
- macOS with Apple Silicon (M1+)

## Quick Start

## Operator Quickstart (Copy/Paste)

```bash
# 0) From repo root
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict

# 1) Backend API (Terminal A)
source venv/bin/activate
uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030 --reload

# 2) UI with backend proxy (Terminal B)
API_PROXY_TARGET="http://127.0.0.1:8030" WATCHPACK_POLLING=true \
  npm --prefix "/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/ui" run dev -- \
  --hostname 127.0.0.1 --port 3040

# 3) Health checks (Terminal C, optional)
curl -s "http://127.0.0.1:8030/api/ui/health"
curl -s "http://127.0.0.1:8030/api/trial/markets?limit=1"

# 4) Open in browser
# http://127.0.0.1:3040
# http://127.0.0.1:3040/trial
```

If `3040` is busy, change to `3041` in the UI command.

### 1. Install Python Dependencies

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
pip install -e ".[dev]"
```

### 2. Configure Ollama (M5 Pro Optimization)

```bash
# Source the M5 Pro optimization script
source config/ollama.sh

# Download models (run once)
ollama pull phi4:14b      # Brain model (~7GB)
ollama pull qwen2.5-coder:7b  # Hands model (~4GB)

# Start Ollama server
ollama serve
```

The optimization script:
- Enables MLX backend (20% faster on M5)
- Keeps models resident (avoids reload delays)
- Allocates 10 CPU threads (M5 has 12 cores)

### 3. Create .env File

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Run Tests

```bash
pytest tests/ -v
```

### 5. Run UI Tests

```bash
# Use npm prefix to avoid cwd resolution issues
npm --prefix "/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/ui" run test
```

### 6. Start Development

See task descriptions in `docs/superpowers/plans/` for implementation tasks.

## Run Services Locally

### Backend UI API

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
source venv/bin/activate
uvicorn kal_predict.api.app:app --host 127.0.0.1 --port 8030 --reload
```

### Frontend Dashboard

```bash
# Start UI with backend proxy target (recommended)
API_PROXY_TARGET="http://127.0.0.1:8030" npm --prefix "/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/ui" run dev -- --hostname 127.0.0.1 --port 3040
```

If the default UI port is unstable or already in use, run on an alternate port:

```bash
API_PROXY_TARGET="http://127.0.0.1:8030" WATCHPACK_POLLING=true npm --prefix "/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/ui" run dev -- --hostname 127.0.0.1 --port 3041
```

Optional: direct frontend API target (fallback behavior supports this):

```bash
export NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8030"
```

## Pre-Credential Mode (Now until Saturday)

Until Kalshi API credentials arrive:
- All tests use mock `MarketDataProvider`
- All execution uses mock `ExecutionProvider`
- No Kalshi write operations enabled

### Pre-Key Phase 2 Status

- Completed in pre-key scope:
  - Trial exchange with manual/auto paper bets
  - Ollama inference integration with fallback and inference-health observability
  - Read-only API hardening and deterministic error envelopes
- Blocked until Kalshi credentials:
  - Real Kalshi read-path onboarding
  - Paper parity validation against real reads

See `docs/operations/pre-key-phase2-status.md` for explicit unblock criteria.

## Saturday Credential Onboarding

When Kalshi credentials arrive:
1. Place private key at path specified in `.env`
2. Set `KALSHI_API_KEY_ID` in `.env`
3. Run credential validation tests
4. Keep `EXECUTION_MODE=paper` in `.env` until Gate F approval

## Logs

Application logs are written to `logs/kal_predict.log` in JSON format.
Review logs daily for anomalies and decision quality (as per audit standard).

## Architecture

- **src/kal_predict/**: Main package
  - `config.py`: Environment-based configuration
  - `logging_setup.py`: Structured logging with trace IDs
  - `trace.py`: Correlation ID management
  - `models.py`: Pydantic schemas (data contracts)
  - `adapters/`: Abstract providers (market data, execution)
  - `core/`: Decision engine (Bayesian, risk gates)
  - `pipeline/`: Orchestration (Brain/Hands, heartbeat)
  - `api/`: Read-only UI API routes (`/api/ui/*`)
  - `services/`: Data aggregation layer for UI API responses
  - `utils/`: Shared utilities

- **tests/**: Unit and integration tests
- **tests/api/**: UI API contract and read-only guardrail tests

- **config/**: Configuration files
  - `ollama.sh`: M5 Pro optimizations
  - `logging.yaml`: Structured logging config

- **docs/**: SDLC documents and plans
- **ui/**: Next.js operator dashboard with read-only `/api/ui/*` views and paper-only `/api/trial/*` actions

## UI Troubleshooting

- **Symptom:** browser shows broken page / random 404/500 from Next dev server.
- **Common cause:** file watcher limit (`EMFILE: too many open files`).
- **Quick recovery:**
  1. Restart UI on a fresh port (for example `3041`).
  2. Use `WATCHPACK_POLLING=true` in dev command.
  3. Keep backend API on `:8030` and verify `GET /api/ui/health` is 200.
  4. Ensure `API_PROXY_TARGET` points to the active backend port.
