"""Unit tests for AdaptiveScoreRegulator dynamic market threshold scaling."""
import pytest
from src.core.adaptive_regulator import AdaptiveScoreRegulator


def test_adaptive_regulator_insufficient_data():
    regulator = AdaptiveScoreRegulator(base_threshold=75.0)
    thresh, regime, _ = regulator.evaluate_regime([])
    assert thresh == 75.0
    assert regime == "NEUTRAL"


def test_adaptive_regulator_bullish_lowers_threshold():
    regulator = AdaptiveScoreRegulator(base_threshold=75.0, min_clamp=70.0)
    # 25 candles with steady upward slope
    klines = [{"close": 60000.0 + i * 200.0} for i in range(25)]
    thresh, regime, _ = regulator.evaluate_regime(klines)
    assert regime == "BULLISH_MOMENTUM"
    assert thresh == pytest.approx(71.0)  # 75.0 - 4.0


def test_adaptive_regulator_bearish_raises_threshold():
    regulator = AdaptiveScoreRegulator(base_threshold=75.0, max_clamp=85.0)
    # Candles sloping downward moderately (-0.9% return)
    klines = [{"close": 65000.0 - i * 25.0} for i in range(25)]
    thresh, regime, _ = regulator.evaluate_regime(klines)
    assert regime == "BEARISH_DEFENSE"
    assert thresh == pytest.approx(81.0)  # 75.0 + 6.0


def test_adaptive_regulator_macro_lockout():
    regulator = AdaptiveScoreRegulator(base_threshold=75.0)
    # Severe drop > 2%
    klines = [{"close": 65000.0} for _ in range(20)]
    klines.extend([{"close": 63000.0}, {"close": 62000.0}])
    thresh, regime, _ = regulator.evaluate_regime(klines)
    assert regime == "MACRO_LOCKOUT"
    assert thresh >= 99.0
