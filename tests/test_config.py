from kal_predict.config import KalshiConfig, OllamaConfig, load_config


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


def test_load_config_succeeds():
    """Test that load_config() initializes successfully."""
    config = load_config()
    assert config.ollama.base_url is not None
    assert config.execution.mode in ("paper", "live")
