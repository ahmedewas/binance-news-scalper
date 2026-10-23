"""Unit tests for TTM Volatility Squeeze Engine."""
from src.core.volatility_squeeze import VolatilitySqueezeDetector


def make_flat_klines(count=30, base_price=100.0, spread=0.1):
    klines = []
    for i in range(count):
        klines.append({
            "open": base_price,
            "high": base_price + spread,
            "low": base_price - spread,
            "close": base_price + (0.01 if i % 2 == 0 else -0.01),
            "volume": 100.0,
        })
    return klines


def test_insufficient_bars():
    detector = VolatilitySqueezeDetector()
    is_sq, is_fired, mom, msg = detector.evaluate([])
    assert is_sq is False
    assert is_fired is False
    assert msg == "INSUFFICIENT_BARS"


def test_in_squeeze_compression():
    detector = VolatilitySqueezeDetector(bb_mult=2.0, kc_mult=2.5)
    # Extremely narrow range forces BB inside KC
    klines = make_flat_klines(35, base_price=100.0, spread=0.01)
    is_sq, is_fired, mom, msg = detector.evaluate(klines)
    assert is_sq is True
    assert is_fired is False
    assert "IN_SQUEEZE" in msg


def test_squeeze_fired_bullish():
    detector = VolatilitySqueezeDetector(bb_mult=2.0, kc_mult=2.5)
    # First 30 candles tightly squeezed
    klines = make_flat_klines(30, base_price=100.0, spread=0.01)
    # Candle 31: massive explosive bullish candle breaking outside BB & KC
    klines.append({
        "open": 100.0,
        "high": 105.0,
        "low": 100.0,
        "close": 104.5,
        "volume": 5000.0,
    })
    is_sq, is_fired, mom, msg = detector.evaluate(klines)
    assert is_fired is True
    assert mom > 0.0
    assert "SQUEEZE_FIRED_BULLISH" in msg
