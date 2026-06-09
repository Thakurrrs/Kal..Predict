from kal_predict.config import ExecutionConfig, FredConfig, KalshiConfig, OllamaConfig, load_config


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


def test_kalshi_base_url_from_env(monkeypatch):
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
