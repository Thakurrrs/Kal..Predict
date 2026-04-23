# Development Setup

## Prerequisites

- Python 3.9+
- Ollama (installed and running)
- macOS with Apple Silicon (M1+)

## Quick Start

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

### 5. Start Development

See task descriptions in `docs/superpowers/plans/` for implementation tasks.

## Pre-Credential Mode (Now until Saturday)

Until Kalshi API credentials arrive:
- All tests use mock `MarketDataProvider`
- All execution uses mock `ExecutionProvider`
- No Kalshi write operations enabled

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
  - `utils/`: Shared utilities

- **tests/**: Unit and integration tests

- **config/**: Configuration files
  - `ollama.sh`: M5 Pro optimizations
  - `logging.yaml`: Structured logging config

- **docs/**: SDLC documents and plans
