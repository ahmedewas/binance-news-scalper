"""Unit tests for Hurst Exponent Chaos and Market Memory Filter."""
from src.core.hurst_filter import HurstFilter


def test_persistent_trend_detection():
    filter_engine = HurstFilter(min_trending_hurst=0.52)
    # Generate persistent linear trend prices
    prices = [10.0 + (i * 0.4) for i in range(40)]
    valid, conf, msg = filter_engine.validate_market_regime(prices)
    assert valid
    assert "Persistent Trend" in msg


def test_chaotic_random_prices():
    filter_engine = HurstFilter(min_trending_hurst=0.52)
    # Ping-pong alternating noise (anti-persistent / chaotic)
    prices = [10.0 + (0.5 if i % 2 == 0 else -0.5) for i in range(40)]
    valid, conf, msg = filter_engine.validate_market_regime(prices)
    assert not valid
    assert "Chaos Noise" in msg or "Random Walk" in msg


def test_insufficient_prices():
    filter_engine = HurstFilter()
    valid, conf, msg = filter_engine.validate_market_regime([10.0, 10.1, 10.2])
    assert not valid
