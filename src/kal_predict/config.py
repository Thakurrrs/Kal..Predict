"""Configuration loader with environment-based secret injection."""

import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).parent.parent.parent / ".env"


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
            with open(self.private_key_path, "r") as f:
                return f.read()
        except OSError as e:
            logger.warning(f"Cannot load private key at {self.private_key_path}: {e}")
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
    trading_enabled: bool = Field(default=True)
    capital_usd: float = Field(default=10000.0)
    max_position_usd: float = Field(default=1000.0)

    model_config = ConfigDict(env_prefix="EXECUTION_")


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

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    kalshi: KalshiConfig = Field(default_factory=KalshiConfig)
    nws: NWSConfig = Field(default_factory=NWSConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    risk_gate: RiskGateConfig = Field(default_factory=RiskGateConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Nested settings classes read from process env; unknown keys must not crash startup.
    model_config = ConfigDict(extra="ignore")


def load_config() -> AppConfig:
    """Load configuration from environment and .env file."""
    load_dotenv(ENV_FILE, override=False)
    config = AppConfig()
    logger.info(
        "Configuration loaded",
        extra={
            "execution_mode": config.execution.mode,
            "kalshi_available": config.kalshi.is_available,
        },
    )
    return config
