"""Unit tests for PrecisionFormatter lot-size and notional sanitizer."""
import pytest
from src.exchange.precision_formatter import PrecisionFormatter


def test_round_down_step():
    # Step size 0.01
    assert PrecisionFormatter.round_down_step(12.3456, 0.01) == pytest.approx(12.34)
    # Step size 0.001
    assert PrecisionFormatter.round_down_step(0.1239, 0.001) == pytest.approx(0.123)
    # Step size 1.0 (integer coins)
    assert PrecisionFormatter.round_down_step(15.9, 1.0) == pytest.approx(15.0)
    # Zero or negative step size
    assert PrecisionFormatter.round_down_step(10.5, 0.0) == pytest.approx(10.5)


def test_sanitize_amount():
    rules = {"step_size": 0.01, "min_amount": 0.01}
    assert PrecisionFormatter.sanitize_amount("SOL/USDT", 1.239, rules) == pytest.approx(1.23)
    assert PrecisionFormatter.sanitize_amount("SOL/USDT", -5.0, rules) == 0.0
    # Empty rules fallback
    assert PrecisionFormatter.sanitize_amount("SOL/USDT", 2.3456789, {}) == pytest.approx(2.345679)


def test_is_notional_valid():
    # 0.1 * 100 = $10.0 (>= 5.0)
    assert PrecisionFormatter.is_notional_valid("SOL/USDT", 100.0, 0.1, min_notional=5.0) is True
    # 0.01 * 100 = $1.0 (< 5.0)
    assert PrecisionFormatter.is_notional_valid("SOL/USDT", 100.0, 0.01, min_notional=5.0) is False
