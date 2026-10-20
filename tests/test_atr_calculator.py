"""Unit tests for ATR Calculator."""
from src.core.atr_calculator import ATRCalculator


def test_atr_calculator_basic():
    calc = ATRCalculator(period=5, tp_multiplier=1.8, sl_multiplier=1.0)
    klines = [
        {"high": 102.0, "low": 98.0, "close": 100.0},
        {"high": 104.0, "low": 99.0, "close": 103.0},
        {"high": 105.0, "low": 101.0, "close": 102.0},
        {"high": 106.0, "low": 100.0, "close": 105.0},
        {"high": 108.0, "low": 103.0, "close": 107.0},
        {"high": 110.0, "low": 105.0, "close": 109.0},
    ]
    atr = calc.compute_atr(klines)
    assert atr > 0.0

    tp_pct, sl_pct, val = calc.calculate_targets(100.0, klines)
    assert 0.008 <= tp_pct <= 0.030
    assert 0.006 <= sl_pct <= 0.015


def test_atr_calculator_empty_klines_safe_defaults():
    calc = ATRCalculator()
    tp_pct, sl_pct, val = calc.calculate_targets(100.0, [])
    assert tp_pct == 0.012
    assert sl_pct == 0.009
    assert val == 0.0
