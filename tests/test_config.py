import pytest

from kal_predict.config import (
    ExecutionConfig,
    FredConfig,
    KalshiConfig,
    OllamaConfig,
    PaperDataConfig,
    PaperSizingConfig,
    load_config,
)


def test_ollama_config_from_env(monkeypatch):
    """Test that OllamaConfig loads from environment variables."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:11434")
    monkeypatch.setenv("OLLAMA_BRAIN_MODEL", "custom-brain:70b")

    config = OllamaConfig()
    assert config.base_url == "http://custom:11434"
    assert config.brain_model == "custom-brain:70b"


def test_kalshi_available_checks_credentials(monkeypatch):
    """Test that Kalshi availability is checked correctly."""
    # Clear any existing env vars first
    monkeypatch.delenv("KALSHI_API_KEY_ID", raising=False)
    monkeypatch.delenv("KALSHI_PRIVATE_KEY_PATH", raising=False)

    config = KalshiConfig()
    assert config.is_available is False

    monkeypatch.setenv("KALSHI_API_KEY_ID", "test-key")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "/tmp/key.pem")
    config = KalshiConfig()
    assert config.is_available is True


def test_kalshi_inline_pem_takes_precedence_and_is_available(monkeypatch):
    """Inline PEM alone (no path) makes Kalshi available and is returned by loader."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    monkeypatch.delenv("KALSHI_PRIVATE_KEY_PATH", raising=False)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    monkeypatch.setenv("KALSHI_API_KEY_ID", "test-key")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PEM", pem)

    config = KalshiConfig()
    assert config.is_available is True
    loaded = config.load_private_key()
    assert loaded is not None
    assert "BEGIN PRIVATE KEY" in loaded


def test_kalshi_inline_pem_normalizes_escaped_newlines(monkeypatch):
    """A single-line .env value using literal \\n is normalized to real newlines."""
    monkeypatch.delenv("KALSHI_PRIVATE_KEY_PATH", raising=False)
    one_line = "-----BEGIN PRIVATE KEY-----\\nMIIBVgIBADANBg\\n-----END PRIVATE KEY-----"
    monkeypatch.setenv("KALSHI_API_KEY_ID", "test-key")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PEM", one_line)

    config = KalshiConfig()
    loaded = config.load_private_key()
    assert loaded is not None
    assert "\\n" not in loaded
    assert loaded.count("\n") == 2


def test_kalshi_not_available_without_any_key(monkeypatch):
    """API key alone, with neither inline nor path, is not available."""
    monkeypatch.delenv("KALSHI_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("KALSHI_PRIVATE_KEY_PEM", raising=False)
    monkeypatch.setenv("KALSHI_API_KEY_ID", "test-key")

    config = KalshiConfig()
    assert config.is_available is False
    """Kalshi API host is configurable for production/demo environments."""
    monkeypatch.setenv("KALSHI_BASE_URL", "https://example.kalshi.test")

    config = KalshiConfig()

    assert config.base_url == "https://example.kalshi.test"


def test_fred_config_api_key_from_env(monkeypatch):
    """FRED key and host are configurable for economics research."""
    monkeypatch.setenv("FRED_API_KEY", "fred-test-key")
    monkeypatch.setenv("FRED_BASE_URL", "https://fred.example.test")

    config = FredConfig()

    assert config.api_key == "fred-test-key"
    assert config.base_url == "https://fred.example.test"
    assert config.is_available is True


def test_paper_data_config_from_env(monkeypatch):
    """Paper data path and source-cache TTLs are runtime configurable."""
    monkeypatch.setenv("PAPER_DATA_DATABASE_PATH", "data/test-paper.db")
    monkeypatch.setenv("PAPER_DATA_NWS_CACHE_TTL_SECONDS", "1200")
    monkeypatch.setenv("PAPER_DATA_FRED_CACHE_TTL_SECONDS", "7200")

    config = PaperDataConfig()

    assert config.database_path == "data/test-paper.db"
    assert config.nws_cache_ttl_seconds == 1200
    assert config.fred_cache_ttl_seconds == 7200


def test_paper_sizing_config_from_env(monkeypatch):
    """Paper sizing risk caps are runtime configurable."""
    monkeypatch.setenv("PAPER_SIZING_BANKROLL_USD", "5000")
    monkeypatch.setenv("PAPER_SIZING_MAX_DOLLARS_PER_TRADE", "75")

    config = PaperSizingConfig()

    assert config.bankroll_usd == 5000.0
    assert config.max_dollars_per_trade == 75.0


def test_load_config_paper_mode_is_safe(monkeypatch):
    """Default paper mode loads without tripping the live guard."""
    monkeypatch.delenv("EXECUTION_MODE", raising=False)
    monkeypatch.delenv("EXECUTION_LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("EXECUTION_LIVE_OPT_IN", raising=False)
    config = load_config()
    assert config.execution.mode == "paper"


def test_load_config_live_without_opt_in_raises(monkeypatch):
    """Live mode without explicit opt-in is refused at startup."""
    from kal_predict.config import LiveModeNotPermittedError

    monkeypatch.setenv("EXECUTION_MODE", "live")
    monkeypatch.delenv("EXECUTION_LIVE_OPT_IN", raising=False)
    with pytest.raises(LiveModeNotPermittedError):
        load_config()


def test_load_config_live_trading_enabled_without_opt_in_raises(monkeypatch):
    """live_trading_enabled alone (mode still paper) also trips the guard."""
    from kal_predict.config import LiveModeNotPermittedError

    monkeypatch.setenv("EXECUTION_MODE", "paper")
    monkeypatch.setenv("EXECUTION_LIVE_TRADING_ENABLED", "true")
    monkeypatch.delenv("EXECUTION_LIVE_OPT_IN", raising=False)
    with pytest.raises(LiveModeNotPermittedError):
        load_config()


def test_load_config_live_with_opt_in_succeeds(monkeypatch):
    """Live mode is allowed only with explicit operator opt-in."""
    monkeypatch.setenv("EXECUTION_MODE", "live")
    monkeypatch.setenv("EXECUTION_LIVE_OPT_IN", "true")
    config = load_config()
    assert config.execution.mode == "live"


def test_load_config_succeeds():
    """Test that load_config() initializes successfully."""
    config = load_config()
    assert config.ollama.base_url is not None
    assert config.execution.mode in ("paper", "live")


def test_execution_config_defaults_keep_live_disabled():
    """Execution defaults must favor paper trading and require 200 resolved trades."""
    config = ExecutionConfig()

    assert config.mode == "paper"
    assert config.paper_trading_enabled is True
    assert config.live_trading_enabled is False
    assert config.promotion_required_resolved_trades == 200


def test_execution_config_env_overrides(monkeypatch):
    """Execution safety controls can be overridden only via explicit env vars."""
    monkeypatch.setenv("EXECUTION_MODE", "live")
    monkeypatch.setenv("EXECUTION_LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("EXECUTION_PAPER_TRADING_ENABLED", "false")
    monkeypatch.setenv("EXECUTION_PROMOTION_REQUIRED_RESOLVED_TRADES", "250")

    config = ExecutionConfig()

    assert config.mode == "live"
    assert config.live_trading_enabled is True
    assert config.paper_trading_enabled is False
    assert config.promotion_required_resolved_trades == 250
