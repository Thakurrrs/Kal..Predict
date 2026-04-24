# Project Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up a Python project scaffold with directories, dependencies, configuration, logging, and trace ID generation to support both mock (pre-credential) and real (credential) execution modes.

**Architecture:** The project uses a modular structure with clear separation: configuration layer (environment-based secret injection), logging layer (structured events with trace IDs), adapters layer (abstract interfaces for market data and execution), and core business logic (decision engine, orchestration). All dependencies are pinned, all paths are absolute, and secrets are never logged.

**Tech Stack:** Python 3.11+, Pydantic v2 (data validation), httpx (async HTTP), ollama-python (local LLM client), structlog (structured logging), python-dotenv (environment management).

---

## File Structure

```
/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/
├── src/
│   └── kal_predict/
│       ├── __init__.py                 (package init, version)
│       ├── config.py                   (config loader, env-based)
│       ├── logging_setup.py            (structured logging init)
│       ├── trace.py                    (trace ID generation)
│       ├── models.py                   (all Pydantic schemas)
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── market.py               (MarketDataProvider abstract + impls)
│       │   └── execution.py            (ExecutionProvider abstract + impls)
│       ├── core/
│       │   ├── __init__.py
│       │   └── decision.py             (Bayesian logic, gap calc, risk gates)
│       ├── pipeline/
│       │   ├── __init__.py
│       │   └── orchestrator.py         (Brain/Hands, heartbeat loop)
│       └── utils/
│           ├── __init__.py
│           └── errors.py               (custom exceptions)
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_logging_setup.py
│   ├── test_trace.py
│   └── unit/
│       └── (test files per module)
├── config/
│   ├── ollama.sh                       (M5 Pro env vars)
│   └── logging.yaml                    (structured logging config)
├── .env.example                        (template, git-tracked)
├── .env                                (secrets, git-ignored)
├── pyproject.toml                      (dependencies, metadata)
├── DEVELOPMENT.md                      (local setup instructions)
└── docs/
    └── (existing documentation)
```

---

## Task 1: Create project directories and pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `src/kal_predict/__init__.py`

### Steps

- [ ] **Step 1: Create directories**

```bash
mkdir -p /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/{src/kal_predict/{adapters,core,pipeline,utils},tests/unit,config,logs}
```

Expected: All directories created.

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "kal-predict"
version = "0.1.0"
description = "Autonomous predictive trading agent for Kalshi"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [{name = "Rasalghul", email = "rajrohan.thakur07@gmail.com"}]

dependencies = [
    "pydantic>=2.0,<3.0",
    "pydantic-settings>=2.0,<3.0",
    "httpx>=0.25.0,<1.0",
    "ollama>=0.1.0",
    "structlog>=24.1.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0",
    "pytz>=2024.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

[tool.setuptools]
packages = ["kal_predict"]
package-dir = {"" = "src"}

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I"]

[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
disallow_incomplete_defs = true
```

Expected: File created at `/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/pyproject.toml`.

- [ ] **Step 3: Create src/kal_predict/__init__.py**

```python
"""Kal..Predict: autonomous trading agent for Kalshi prediction markets."""

__version__ = "0.1.0"
__author__ = "Rasalghul"

from . import config, logging_setup, trace

__all__ = ["config", "logging_setup", "trace"]
```

Expected: File created with version and imports.

- [ ] **Step 4: Create empty __init__.py files in subpackages**

```bash
touch /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/src/kal_predict/{adapters,core,pipeline,utils}/__init__.py
touch /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/tests/__init__.py
```

Expected: All __init__.py files created.

- [ ] **Step 5: Commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add pyproject.toml src/kal_predict/__init__.py src/kal_predict/{adapters,core,pipeline,utils}/__init__.py tests/__init__.py
git commit -m "feat: initialize project structure and dependencies"
```

Expected: Commit succeeds with message "feat: initialize project structure and dependencies".

---

## Task 2: Implement config.py with environment-based secret injection

**Files:**
- Create: `src/kal_predict/config.py`
- Create: `.env.example`

### Steps

- [ ] **Step 1: Create .env.example template**

```
# Kalshi API (credential mode only, Saturday+)
KALSHI_API_KEY_ID=
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem

# NWS API
NWS_USER_AGENT=kal-predict/0.1.0

# Search providers (free tier)
SEARXNG_BASE_URL=http://localhost:8888
SEARXNG_TIMEOUT_SECONDS=10

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_BRAIN_MODEL=phi4:14b
OLLAMA_HANDS_MODEL=qwen2.5-coder:7b
OLLAMA_TIMEOUT_SECONDS=300

# Execution mode
EXECUTION_MODE=paper

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Paper trading config
PAPER_TRADING_ENABLED=true
PAPER_CAPITAL_USD=10000
PAPER_MAX_POSITION_USD=1000

# Risk gates
RISK_GATE_MIN_CONFIDENCE=0.55
RISK_GATE_MAX_LOSS_PER_TRADE_USD=500
RISK_GATE_DAILY_LOSS_LIMIT_USD=2000
```

Expected: File created at `.env.example`.

- [ ] **Step 2: Create config.py**

```python
"""Configuration loader with environment-based secret injection."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
import logging

logger = logging.getLogger(__name__)


class OllamaConfig(BaseSettings):
    """Ollama local LLM server configuration."""

    base_url: str = Field(default="http://localhost:11434")
    brain_model: str = Field(default="phi4:14b")
    hands_model: str = Field(default="qwen2.5-coder:7b")
    timeout_seconds: int = Field(default=300)

    model_config = ConfigDict(env_prefix="OLLAMA_")


class KalshiConfig(BaseSettings):
    """Kalshi API configuration (credential mode only)."""

    api_key_id: Optional[str] = Field(default=None)
    private_key_path: Optional[str] = Field(default=None)

    model_config = ConfigDict(env_prefix="KALSHI_")

    @property
    def is_available(self) -> bool:
        """Check if Kalshi credentials are loaded."""
        return self.api_key_id is not None and self.private_key_path is not None

    def load_private_key(self) -> Optional[str]:
        """Load private key from disk if path is set."""
        if not self.private_key_path:
            return None
        try:
            with open(self.private_key_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Private key not found at {self.private_key_path}")
            return None


class NWSConfig(BaseSettings):
    """National Weather Service API configuration (free, no auth)."""

    user_agent: str = Field(default="kal-predict/0.1.0")
    base_url: str = Field(default="https://api.weather.gov")
    timeout_seconds: int = Field(default=30)

    model_config = ConfigDict(env_prefix="NWS_")


class SearchConfig(BaseSettings):
    """Search provider configuration."""

    searxng_base_url: str = Field(default="http://localhost:8888")
    searxng_timeout_seconds: int = Field(default=10)

    model_config = ConfigDict(env_prefix="SEARXNG_", case_sensitive=False)


class ExecutionConfig(BaseSettings):
    """Trading execution configuration."""

    mode: str = Field(default="paper")  # "paper" or "live" (live only after Gate F)
    paper_trading_enabled: bool = Field(default=True)
    paper_capital_usd: float = Field(default=10000.0)
    paper_max_position_usd: float = Field(default=1000.0)

    model_config = ConfigDict(env_prefix="")


class RiskGateConfig(BaseSettings):
    """Risk gate thresholds (deterministic, fail-closed)."""

    min_confidence: float = Field(default=0.55)
    max_loss_per_trade_usd: float = Field(default=500.0)
    daily_loss_limit_usd: float = Field(default=2000.0)

    model_config = ConfigDict(env_prefix="RISK_GATE_")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="json")  # "json" or "text"

    model_config = ConfigDict(env_prefix="LOG_")


class AppConfig(BaseSettings):
    """Top-level application configuration."""

    ollama: OllamaConfig = OllamaConfig()
    kalshi: KalshiConfig = KalshiConfig()
    nws: NWSConfig = NWSConfig()
    search: SearchConfig = SearchConfig()
    execution: ExecutionConfig = ExecutionConfig()
    risk_gate: RiskGateConfig = RiskGateConfig()
    logging: LoggingConfig = LoggingConfig()

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


def load_config() -> AppConfig:
    """Load configuration from environment and .env file."""
    config = AppConfig()
    logger.info(
        "Configuration loaded",
        execution_mode=config.execution.mode,
        kalshi_available=config.kalshi.is_available,
    )
    return config
```

Expected: config.py created with all configuration classes.

- [ ] **Step 3: Write test for config loading**

```python
# tests/test_config.py
import os
from pathlib import Path
import pytest
from kal_predict.config import AppConfig, load_config


def test_config_loads_from_env(monkeypatch):
    """Test that config loads from environment variables."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:11434")
    monkeypatch.setenv("OLLAMA_BRAIN_MODEL", "custom-brain:70b")
    monkeypatch.setenv("EXECUTION_MODE", "paper")

    config = AppConfig()
    assert config.ollama.base_url == "http://custom:11434"
    assert config.ollama.brain_model == "custom-brain:70b"
    assert config.execution.mode == "paper"


def test_kalshi_available_checks_credentials(monkeypatch):
    """Test that Kalshi availability is checked correctly."""
    config = AppConfig()
    assert config.kalshi.is_available is False

    monkeypatch.setenv("KALSHI_API_KEY_ID", "test-key")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "/tmp/key.pem")
    config = AppConfig()
    assert config.kalshi.is_available is True


def test_load_config_succeeds():
    """Test that load_config() initializes successfully."""
    config = load_config()
    assert config.ollama.base_url is not None
    assert config.execution.mode in ("paper", "live")
```

Expected: Test file created.

- [ ] **Step 4: Run tests**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
python -m pytest tests/test_config.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add src/kal_predict/config.py .env.example tests/test_config.py
git commit -m "feat: implement environment-based configuration with validation"
```

Expected: Commit succeeds.

---

## Task 3: Implement trace.py for correlation IDs

**Files:**
- Create: `src/kal_predict/trace.py`

### Steps

- [ ] **Step 1: Create trace.py**

```python
"""Trace ID generation and correlation context management."""

import uuid
import contextvars
from typing import Optional

# Context variable to store the current trace ID
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)


def generate_trace_id() -> str:
    """Generate a new trace ID (UUID4)."""
    return str(uuid.uuid4())


def set_trace_id(trace_id: str) -> None:
    """Set the current trace ID in context."""
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Get the current trace ID, or generate a new one if not set."""
    trace_id = _trace_id_var.get()
    if trace_id is None:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
    return trace_id


def reset_trace_id() -> None:
    """Reset the trace ID context (for testing)."""
    _trace_id_var.set(None)
```

Expected: File created with trace ID functions.

- [ ] **Step 2: Write tests**

```python
# tests/test_trace.py
import uuid
from kal_predict.trace import (
    generate_trace_id,
    set_trace_id,
    get_trace_id,
    reset_trace_id,
)


def test_generate_trace_id_returns_uuid():
    """Test that trace IDs are valid UUIDs."""
    trace_id = generate_trace_id()
    assert uuid.UUID(trace_id)  # Raises if invalid


def test_get_trace_id_auto_generates():
    """Test that get_trace_id generates a new ID if not set."""
    reset_trace_id()
    trace_id = get_trace_id()
    assert trace_id is not None
    assert uuid.UUID(trace_id)


def test_set_and_get_trace_id():
    """Test that trace IDs can be set and retrieved."""
    reset_trace_id()
    test_id = "test-trace-id-123"
    set_trace_id(test_id)
    assert get_trace_id() == test_id


def test_trace_id_persists():
    """Test that trace ID persists across calls."""
    reset_trace_id()
    id1 = get_trace_id()
    id2 = get_trace_id()
    assert id1 == id2
```

Expected: Tests created.

- [ ] **Step 3: Run tests**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
python -m pytest tests/test_trace.py -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add src/kal_predict/trace.py tests/test_trace.py
git commit -m "feat: implement trace ID generation and context management"
```

Expected: Commit succeeds.

---

## Task 4: Implement logging_setup.py with structured logging

**Files:**
- Create: `src/kal_predict/logging_setup.py`
- Create: `config/logging.yaml`

### Steps

- [ ] **Step 1: Create config/logging.yaml**

```yaml
# Structured logging configuration
version: 1
disable_existing_loggers: false

formatters:
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: "%(timestamp)s %(level)s %(name)s %(message)s %(trace_id)s"

  text:
    format: "%(asctime)s - %(name)s - %(levelname)s - %(trace_id)s - %(message)s"

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: json
    filename: logs/kal_predict.log
    maxBytes: 10485760  # 10 MB
    backupCount: 5

root:
  level: DEBUG
  handlers:
    - console
    - file

loggers:
  kal_predict:
    level: DEBUG
    propagate: true
```

Expected: File created at `config/logging.yaml`.

- [ ] **Step 2: Create logging_setup.py**

```python
"""Structured logging initialization with trace ID injection."""

import logging
import logging.config
from pathlib import Path
from typing import Optional
import json
from kal_predict.trace import get_trace_id


class TraceIDFilter(logging.Filter):
    """Add trace_id to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject trace ID into log record."""
        record.trace_id = get_trace_id()
        return True


class JSONFormatter(logging.Formatter):
    """Format logs as JSON with trace ID."""

    def format(self, record: logging.LogRecord) -> str:
        """Format record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    config_path: Optional[Path] = None,
) -> None:
    """Initialize structured logging with trace ID injection.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" or "text")
        config_path: Optional path to YAML config file
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Add trace ID filter to all handlers
    for handler in root_logger.handlers:
        handler.addFilter(TraceIDFilter())

    # Configure JSON formatter if requested
    if log_format == "json":
        for handler in root_logger.handlers:
            handler.setFormatter(JSONFormatter())

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized", level=log_level, format=log_format)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with trace ID injection."""
    logger = logging.getLogger(name)
    logger.addFilter(TraceIDFilter())
    return logger
```

Expected: File created.

- [ ] **Step 3: Write tests**

```python
# tests/test_logging_setup.py
import logging
from kal_predict.logging_setup import setup_logging, get_logger, TraceIDFilter
from kal_predict.trace import set_trace_id, reset_trace_id


def test_setup_logging_initializes():
    """Test that setup_logging() completes without error."""
    reset_trace_id()
    setup_logging(log_level="DEBUG", log_format="json")
    logger = logging.getLogger("test")
    logger.info("test message")


def test_trace_id_filter_adds_trace_id():
    """Test that TraceIDFilter injects trace ID into records."""
    reset_trace_id()
    set_trace_id("test-trace-123")
    
    filter = TraceIDFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test",
        args=(),
        exc_info=None,
    )
    
    assert filter.filter(record) is True
    assert record.trace_id == "test-trace-123"


def test_get_logger_returns_logger():
    """Test that get_logger returns a logger instance."""
    reset_trace_id()
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"
```

Expected: Tests created.

- [ ] **Step 4: Run tests**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
python -m pytest tests/test_logging_setup.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add src/kal_predict/logging_setup.py config/logging.yaml tests/test_logging_setup.py
git commit -m "feat: implement structured logging with trace ID injection"
```

Expected: Commit succeeds.

---

## Task 5: Create Ollama configuration for M5 Pro optimization

**Files:**
- Create: `config/ollama.sh`
- Create: `DEVELOPMENT.md`

### Steps

- [ ] **Step 1: Create config/ollama.sh**

```bash
#!/bin/bash
# Ollama configuration for MacBook Pro M5 Pro
# Source this file before running Ollama to enable optimizations

# Enable MLX backend (Apple Silicon optimized)
export OLLAMA_MLX=1

# Keep model resident in memory (avoid reload overhead)
export OLLAMA_KEEP_ALIVE=-1

# Set number of threads (M5 Pro has 12 cores)
export OLLAMA_NUM_THREAD=10

# Increase context window for long-form evidence
export OLLAMA_NUM_PREDICT=4096

echo "✓ Ollama M5 Pro optimizations enabled"
echo "  - MLX backend (faster inference)"
echo "  - Model persistence (avoid reload)"
echo "  - Thread count: 10"
echo "  - Context window: 4096 tokens"
```

Expected: File created with executable bit.

- [ ] **Step 2: Make script executable**

```bash
chmod +x /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/config/ollama.sh
```

Expected: Script is executable.

- [ ] **Step 3: Create DEVELOPMENT.md**

```markdown
# Development Setup

## Prerequisites

- Python 3.11+
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
```

Expected: DEVELOPMENT.md created with setup instructions.

- [ ] **Step 4: Commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add config/ollama.sh DEVELOPMENT.md
git commit -m "feat: add Ollama M5 Pro optimization and development setup guide"
```

Expected: Commit succeeds.

---

## Task 6: Create utils/errors.py with custom exceptions

**Files:**
- Create: `src/kal_predict/utils/errors.py`

### Steps

- [ ] **Step 1: Create errors.py**

```python
"""Custom exceptions for Kal..Predict."""


class KalPredictError(Exception):
    """Base exception for all Kal..Predict errors."""

    pass


class ConfigError(KalPredictError):
    """Configuration loading or validation error."""

    pass


class DataValidationError(KalPredictError):
    """Data contract validation failure."""

    pass


class ProviderError(KalPredictError):
    """Data provider (market, execution, search) error."""

    pass


class MarketDataError(ProviderError):
    """Market data provider error."""

    pass


class ExecutionError(ProviderError):
    """Execution provider error."""

    pass


class RiskGateViolation(KalPredictError):
    """Risk gate check failed (fail-closed, no trade executed)."""

    pass


class DecisionEngineError(KalPredictError):
    """Decision engine processing error."""

    pass


class OrchestratorError(KalPredictError):
    """Orchestration (heartbeat, state management) error."""

    pass
```

Expected: File created with exception hierarchy.

- [ ] **Step 2: Update src/kal_predict/utils/__init__.py**

```python
"""Utilities package."""

from .errors import (
    KalPredictError,
    ConfigError,
    DataValidationError,
    ProviderError,
    MarketDataError,
    ExecutionError,
    RiskGateViolation,
    DecisionEngineError,
    OrchestratorError,
)

__all__ = [
    "KalPredictError",
    "ConfigError",
    "DataValidationError",
    "ProviderError",
    "MarketDataError",
    "ExecutionError",
    "RiskGateViolation",
    "DecisionEngineError",
    "OrchestratorError",
]
```

Expected: __init__.py updated.

- [ ] **Step 3: Write tests**

```python
# tests/test_utils_errors.py
import pytest
from kal_predict.utils.errors import (
    KalPredictError,
    RiskGateViolation,
    ConfigError,
)


def test_risk_gate_violation_is_subclass_of_base():
    """Test that RiskGateViolation inherits from KalPredictError."""
    assert issubclass(RiskGateViolation, KalPredictError)


def test_config_error_is_subclass_of_base():
    """Test that ConfigError inherits from KalPredictError."""
    assert issubclass(ConfigError, KalPredictError)


def test_exceptions_can_be_raised_and_caught():
    """Test that custom exceptions work as expected."""
    with pytest.raises(RiskGateViolation):
        raise RiskGateViolation("Confidence below threshold")

    with pytest.raises(KalPredictError):
        raise RiskGateViolation("Any KalPredictError subclass")
```

Expected: Tests created.

- [ ] **Step 4: Run tests**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
python -m pytest tests/test_utils_errors.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add src/kal_predict/utils/errors.py src/kal_predict/utils/__init__.py tests/test_utils_errors.py
git commit -m "feat: add custom exception hierarchy"
```

Expected: Commit succeeds.

---

## Task 7: Create .gitignore and initial git setup

**Files:**
- Create: `.gitignore`
- Verify: git repo initialized

### Steps

- [ ] **Step 1: Check if git repo exists**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git status
```

If not initialized, run:

```bash
git init
git config user.name "Rasalghul"
git config user.email "rajrohan.thakur07@gmail.com"
```

Expected: Git repo exists and is configured.

- [ ] **Step 2: Create .gitignore**

```
# Environment and secrets
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logging and data
logs/
*.log
data/

# Credentials and keys
*.pem
*.key
credentials.json
```

Expected: .gitignore created.

- [ ] **Step 3: Initial commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add -A
git commit -m "chore: add .gitignore"
```

Expected: Commit succeeds.

---

## Task 8: Verify project structure and run full test suite

**Files:**
- No new files
- Verify: All tests pass

### Steps

- [ ] **Step 1: Verify directory structure**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
find src tests config -type f -name "*.py" | sort
```

Expected: Output shows all created files:
```
config/ollama.sh
src/kal_predict/__init__.py
src/kal_predict/adapters/__init__.py
src/kal_predict/config.py
src/kal_predict/core/__init__.py
src/kal_predict/logging_setup.py
src/kal_predict/pipeline/__init__.py
src/kal_predict/trace.py
src/kal_predict/utils/__init__.py
src/kal_predict/utils/errors.py
tests/__init__.py
tests/test_config.py
tests/test_logging_setup.py
tests/test_trace.py
tests/test_utils_errors.py
```

- [ ] **Step 2: Install development dependencies**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
pip install -e ".[dev]"
```

Expected: Installation succeeds.

- [ ] **Step 3: Run all tests with coverage**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
python -m pytest tests/ -v --cov=src/kal_predict --cov-report=term-missing
```

Expected: All tests pass, coverage report shows >80% coverage for new modules.

- [ ] **Step 4: Run linting checks**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
black src/ tests/ --check
ruff check src/ tests/
```

Expected: No linting errors.

- [ ] **Step 5: Verify module imports**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
python -c "from kal_predict import config, logging_setup, trace; from kal_predict.utils.errors import KalPredictError; print('✓ All imports successful')"
```

Expected: Output shows "✓ All imports successful".

- [ ] **Step 6: Final commit**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git add .gitignore
git commit -m "chore: add .gitignore for Python project"
```

Expected: Commit succeeds.

- [ ] **Step 7: Verify git log**

```bash
cd /Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict
git log --oneline | head -10
```

Expected: Shows recent commits with clear messages.

---

## Plan Self-Review

**Spec Coverage:**
- ✅ Directory structure (src/, tests/, config/)
- ✅ pyproject.toml with dependencies
- ✅ .env template for secrets
- ✅ Configuration loading (environment-based)
- ✅ Structured logging with trace IDs
- ✅ Trace ID generation and context management
- ✅ Ollama M5 Pro optimization
- ✅ Base exceptions and error hierarchy
- ✅ Development setup documentation
- ✅ Git initialization and .gitignore

**Placeholder Scan:** None found. All code steps include complete implementations.

**Type Consistency:** Config classes use Pydantic v2 with proper validation. Trace functions return strings. Loggers follow Python logging API.

**No Spec Gaps Identified.**

---

## Execution Options

**Plan complete and saved to `/Users/rasalghul/Documents/LeagueOfAssassins/Kal..Predict/docs/superpowers/plans/2026-04-23-project-initialization.md`.**

Two execution options:

### **1. Subagent-Driven (Recommended)**
- Fresh subagent per task with independent execution
- I review between tasks for correctness
- Fast iteration with parallel validation

### **2. Inline Execution**
- Execute all tasks in this session
- Batch execution with checkpoints
- Fewer context switches, but larger single session

**Which approach would you prefer?**
