"""Unit tests for PrecisionFormatter lot-size and notional sanitizer."""
import pytest
from src.exchange.precision_formatter import PrecisionFormatter


def test_round_down_step():
    # Decimal powers of 10
    assert PrecisionFormatter.round_down_step(12.3456, 0.01) == pytest.approx(12.34)
    assert PrecisionFormatter.round_down_step(0.1239, 0.001) == pytest.approx(0.123)
    assert PrecisionFormatter.round_down_step(15.9, 1.0) == pytest.approx(15.0)
    # Non-decimal steps (Binance specific steps: 0.2, 0.05, 2.0)
    assert PrecisionFormatter.round_down_step(0.35, 0.2) == pytest.approx(0.20)
    assert PrecisionFormatter.round_down_step(0.17, 0.05) == pytest.approx(0.15)
    assert PrecisionFormatter.round_down_step(9.5, 2.0) == pytest.approx(8.0)
    # Zero or negative step size
    assert PrecisionFormatter.round_down_step(10.5, 0.0) == pytest.approx(10.5)


def test_sanitize_amount():
    rules = {"step_size": 0.05, "min_amount": 0.05}
    assert PrecisionFormatter.sanitize_amount("SOL/USDT", 0.179, rules) == pytest.approx(0.15)
    assert PrecisionFormatter.sanitize_amount("SOL/USDT", -5.0, rules) == 0.0
    # Empty rules fallback
    assert PrecisionFormatter.sanitize_amount("SOL/USDT", 2.3456789, {}) == pytest.approx(2.345679)


def test_is_notional_valid():
    # 0.1 * 100 = $10.0 (>= 5.0)
    assert PrecisionFormatter.is_notional_valid("SOL/USDT", 100.0, 0.1, min_notional=5.0) is True
    # 0.01 * 100 = $1.0 (< 5.0)
    assert PrecisionFormatter.is_notional_valid("SOL/USDT", 100.0, 0.01, min_notional=5.0) is False
