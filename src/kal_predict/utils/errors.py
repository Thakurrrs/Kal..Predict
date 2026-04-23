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
