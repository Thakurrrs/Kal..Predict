import pytest

from kal_predict.utils.errors import (
    ConfigError,
    KalPredictError,
    RiskGateViolation,
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
