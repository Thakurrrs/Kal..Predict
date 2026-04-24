# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kal..Predict** is an autonomous predictive trading agent for Kalshi (CFTC-regulated prediction markets). The goal is 60-70% forecast accuracy on weather markets through Bayesian probability updates combined with real-time evidence ingestion.

**Key Context:**
- Early stage (v0.1.0), currently in SDLC Build phase (Gate D - Verification Ready CLEARED)
- Runs on Apple Silicon (MacBook Pro M5 Pro) with local Ollama LLM inference
- **Free-tier only** — no paid APIs (NWS, SearXNG, FRED all free)
- **Pre-credential mode until Saturday** — all tests use mock Kalshi adapters until API credentials arrive
- **SDLC-first development** — documentation gates ALL implementation (no code without approved docs)
- **Gate D cleared 2026-04-23** — Replay harness and Brier/calibration criteria locked. Ready for Gate E (Paper Release)

## SDLC Development Workflow

**This project follows a documentation-first SDLC with mandatory gate approvals.** Read `docs/governance/sdlc-charter.md` for the full process.

### Stage Gates

| Gate | Status | Focus |
|------|--------|-------|
| **A** | ✅ Approved | Requirements (PRD, scope, success metrics) |
| **B** | ✅ Approved | Architecture (ADRs, data contracts, threat model) |
| **C** | ✅ Approved | Engineering (API specs, logging standards, error policies) |
| **D** | ✅ Approved | Verification (test strategy, replay harness, pass criteria) |
| **E** | 🏗️ In Progress | Paper Release (paper mode end-to-end, risk gates enforced) |
| **F** | ⏳ Pending | Limited Live (paper metrics stable, founder sign-off) |

**Mandatory rule:** No code change proceeds until gate-critical docs are approved and status-marked in `docs/`.

### Architecture: Brain and Hands

Per ADR-0001 (`docs/architecture/adr-0001-system-boundaries.md`):

- **Brain**: Supervisory LLM (reasoning layer) — generates high-level thesis and decomposes into tasks
  - Models: Qwen 3.5 35B (quantized) or API-based for larger reasoning
  - Does NOT execute trades; only interprets evidence and updates probabilities

- **Hands**: Fast execution LLM (deterministic layer) — claims tasks and retrieves data
  - Models: Qwen 2.5 Coder 7B or Phi 4 14B (runs locally)
  - Executes deterministic logic only: fetch data, calculate gaps, check risk gates

- **Communication**: Shared filesystem workspace (heartbeat manifest, task queue, audit logs)

**Fail-closed constraint:** Any risk gate failure immediately halts decision propagation — no trade intent generated. Risk gates are deterministic (no LLM judgment).

## Quick Start

### Installation

```bash
# Install Python 3.11+ and Ollama first

cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict

# Install project and dev dependencies
pip install -e ".[dev]"

# Copy env template and configure
cp .env.example .env
# Edit .env with your Ollama/search provider settings
```

### Configure Ollama (M5 Pro)

```bash
# Enable M5 Pro optimizations (20% faster inference)
source config/ollama.sh

# Download models (one-time, ~11GB total)
ollama pull phi4:14b
ollama pull qwen2.5-coder:7b

# Start Ollama server (leave running)
ollama serve
```

### Common Commands

```bash
# Run all tests
pytest tests/ -v

# Run single test
pytest tests/test_config.py::test_config_loads_from_env -v

# Run with coverage
pytest tests/ --cov=src/kal_predict --cov-report=html

# Code quality checks
black src/ tests/          # Auto-format
ruff check src/ tests/     # Lint (E, F, W, I rules)
mypy src/                  # Type check (strict mode)

# Run full check suite (before committing)
black src/ tests/ && ruff check src/ tests/ && mypy src/ && pytest tests/
```

## Project Structure

```
src/kal_predict/
├── __init__.py              # Package metadata only (version, author)
├── config.py                # Pydantic-based config loader (env-based secrets)
├── logging_setup.py         # Structured logging with trace ID injection
├── trace.py                 # Correlation ID generation (contextvars-based)
├── models.py                # All Pydantic data schemas (contracts)
├── adapters/
│   ├── market.py           # Abstract MarketDataProvider (Kalshi + mock impls)
│   └── execution.py        # Abstract ExecutionProvider (paper + mock impls)
├── core/
│   └── decision.py         # Decision engine: Bayesian logic, gap calc, risk gates
├── pipeline/
│   └── orchestrator.py     # Heartbeat loop, Brain/Hands, state recovery
└── utils/
    ├── errors.py           # Custom exception hierarchy
    └── (shared utilities)

tests/                       # Unit and integration tests
├── test_config.py
├── test_logging_setup.py
├── test_trace.py
└── unit/                   # (organized by module)

config/
├── ollama.sh              # M5 Pro env var script
└── logging.yaml           # Structured logging config (if used)

docs/
├── README.md              # Doc index
├── governance/            # SDLC, RACI, roles
├── product/               # PRD, scope, metrics
├── architecture/          # ADRs, data contracts
├── engineering/           # API specs, error handling
├── quality/               # Test strategy, pass criteria
├── security/              # Threat model, secrets policy
├── operations/            # Runbooks, incident response
├── compliance/            # Audit logging, change mgmt
└── superpowers/plans/     # Implementation plans (from subagent-driven development)

.env.example               # Config template (tracked)
.env                       # Secrets (git-ignored)
pyproject.toml             # Dependencies and tool config
```

## Key Design Patterns and Constraints

### 1. Configuration is Environment-Based (Secrets Never Logged)

- All secrets loaded from `.env` at runtime via Pydantic BaseSettings
- `.env` is git-ignored; `.env.example` is tracked as template
- Secrets never printed in logs (trace IDs and decision details, yes; API keys, no)
- See `src/kal_predict/config.py` for the pattern

### 2. Structured Logging with Trace IDs (Audit Trail)

- Every decision, error, and API call includes a `trace_id` (UUID4 context var)
- Logs are JSON format with required fields per audit standard (`docs/compliance/audit-logging-standard.md`)
- Required fields: timestamp, level, logger, message, trace_id, event_type, actor, risk_gate_result
- Use `from kal_predict.logging_setup import get_logger` to get a logger with trace injection

### 3. Data Contracts with Pydantic v2

- All data models in `src/kal_predict/models.py` use Pydantic BaseModel
- Contracts must include `schemaVersion` field for compatibility across versions
- See `docs/architecture/data-contracts.md` for required schemas:
  - MarketSnapshot (bid/ask, volume, timestamp)
  - EvidenceItem (source, claim, confidenceHint, retrievedAt)
  - Forecast (priorProbability, modelProbability, mixAlpha, mixedProbability)
  - Decision (edge, expectedValue, riskGateResult)
  - TradeIntent (side, maxPrice, size, mode=paper|live)
  - AuditEvent (traceId, eventType, actor, status)

### 4. Fail-Closed Risk Gates (No Bypass Path)

- Risk gate checks are deterministic, not LLM-based
- If a risk gate fails (confidence < threshold, daily loss limit hit, etc.), execution halts immediately
- No manual override or bypass in code — only operational kill switch (documented in incident runbook)
- Trade intent is never generated if any gate fails

### 5. Pre-Credential vs Credential Mode

Until Saturday when Kalshi API credentials arrive:
- All market data comes from `MockMarketDataProvider` (fake data)
- All execution uses `MockExecutionProvider` (no real orders, simulated fills)
- Kalshi read path disabled; write path explicitly disabled
- Post-Saturday, enable Kalshi read with smoke tests before any writes

### 6. Abstract Providers (Adapters for Switching Implementations)

- `MarketDataProvider` and `ExecutionProvider` are abstract base classes
- Concrete impls: `KalshiMarketDataProvider`, `MockMarketDataProvider`, `PaperExecutionProvider`, `MockExecutionProvider`
- Allows tests and pre-credential work to use mocks without touching real APIs
- See `docs/engineering/api-spec.md` for provider contracts

## Testing Strategy

Per `docs/quality/test-strategy.md`:

### Test Levels (in order of implementation)

1. **Unit tests** — Individual functions, config loading, error handling
2. **Integration tests** — Provider interactions, end-to-end decision flow
3. **Replay tests** — Historical backtest with recorded market data (Brier score validation)
4. **Paper-trading tests** — Continuous paper mode with simulated fills (risk gate validation)

### Quality Gates for Release

- **Coverage:** >80% for new modules (measured with pytest-cov)
- **Linting:** No errors from black/ruff (line length 100, E/F/W/I rules)
- **Type safety:** Strict mypy (check_untyped_defs, disallow_incomplete_defs)
- **Replay benchmark:** Brier score better than market baseline over sample data
- **Paper mode:** Zero risk gate violations over 24h+ run

### Running Tests

```bash
# Single test
pytest tests/test_config.py::test_config_loads_from_env -v

# All tests in a file
pytest tests/test_config.py -v

# All tests with coverage
pytest tests/ -v --cov=src/kal_predict --cov-report=term-missing

# Watch mode (with pytest-watch, if installed)
ptw tests/
```

## Documentation Standards

Every document in `docs/` must include:

```yaml
Metadata:
  - Owner: (who is responsible)
  - Reviewers: (who reviews/approves)
  - Approver: (final sign-off)
  - Version: (e.g., 1.0.0)
  - Last Updated: (date)
  - Status: (Draft, In Review, Approved)
```

### Where Each Type of Doc Lives

| Document | Location | Gate |
|----------|----------|------|
| PRD, scope, metrics | `docs/product/prd-v1.md` | A |
| Architecture decisions | `docs/architecture/adr-*.md` | B |
| Data contracts | `docs/architecture/data-contracts.md` | B |
| Threat model | `docs/security/threat-model.md` | B |
| API specs | `docs/engineering/api-spec.md` | C |
| Test strategy | `docs/quality/test-strategy.md` | D |
| Runbooks | `docs/operations/runbook-*.md` | E |
| Incident response | `docs/operations/incident-response.md` | E |
| Secrets policy | `docs/security/secrets-policy.md` | C |
| Audit logging | `docs/compliance/audit-logging-standard.md` | C |
| Change management | `docs/compliance/change-management.md` | C |

## Error Handling and Exceptions

Custom exceptions in `src/kal_predict/utils/errors.py`:

```
KalPredictError (base)
├── ConfigError                  # Config loading/validation
├── DataValidationError          # Data contract violations
├── ProviderError
│   ├── MarketDataError          # Market data retrieval
│   └── ExecutionError           # Order execution
├── RiskGateViolation            # Risk gate check failed (fail-closed)
├── DecisionEngineError          # Decision logic error
└── OrchestratorError            # Heartbeat/state management
```

**All exceptions must be caught and logged with trace_id before propagating.**

## Before Committing

```bash
# 1. Run format and checks
black src/ tests/
ruff check src/ tests/
mypy src/

# 2. Run tests
pytest tests/ -v

# 3. Update or create gate-critical docs if you changed behavior
# (e.g., new risk gate thresholds need threat model update)

# 4. Commit with conventional message (feat:, fix:, docs:, test:)
git commit -m "feat: add new decision gate for position sizing"

# 5. Link to related docs/ADRs in commit body or PR description
```

## Operational Notes

### Daily Operations (After Gate E - Paper Release)

- Review `logs/kal_predict.log` (JSON format, one event per line)
- Check daily anomaly report (error counts, decision spikes, stale data alerts)
- Monitor Brier score drift over time (per audit logging standard)

### Saturday Credential Onboarding (Gate C → Live Prep)

When Kalshi credentials arrive:
1. Place private key at path in `.env` (KALSHI_PRIVATE_KEY_PATH)
2. Set `KALSHI_API_KEY_ID` in `.env`
3. Run credential smoke tests (check auth, signed requests, rate limits)
4. Keep `EXECUTION_MODE=paper` until Gate F approval
5. Monitor real market data freshness and decision quality

### Kill Switch (Emergency)

If an incident occurs:
1. Set `EXECUTION_MODE=paper` in `.env` (or comment out trade execution in code)
2. Restart the application
3. Document the incident with trace IDs in the incident log
4. Follow incident response playbook (`docs/operations/incident-response.md`)

## References

- **Architecture:** `docs/architecture/adr-0001-system-boundaries.md`
- **SDLC Process:** `docs/governance/sdlc-charter.md`
- **API Contracts:** `docs/engineering/api-spec.md`
- **Data Schemas:** `docs/architecture/data-contracts.md`
- **Test Requirements:** `docs/quality/test-strategy.md`
- **Threat & Mitigations:** `docs/security/threat-model.md`
- **Audit & Logging:** `docs/compliance/audit-logging-standard.md`

## Development Tools

- **Local LLM:** Ollama (M5 Pro optimized with MLX backend)
- **Async HTTP:** httpx (for API calls, search, weather data)
- **Config:** pydantic-settings (env-based secret injection)
- **Logging:** structlog (JSON events with trace IDs)
- **Testing:** pytest + pytest-asyncio + pytest-cov
- **Code Quality:** black (formatter), ruff (linter), mypy (type checker)
