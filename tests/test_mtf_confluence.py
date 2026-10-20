"""Unit tests for Multi-Timeframe Confluence Engine."""
from src.core.mtf_confluence import MultiTimeframeConfluence


def test_mtf_bullish_trend():
    mtf = MultiTimeframeConfluence(ema_fast=9, ema_slow=21)
    # 25 candles in steady uptrend
    klines_15m = [
        {"high": 100 + i * 2, "low": 98 + i * 2, "close": 99 + i * 2, "volume": 1000}
        for i in range(25)
    ]
    is_aligned, reason = mtf.check_higher_timeframe(klines_15m)
    assert is_aligned is True
    assert "MTF_BULLISH_CONFLUENCE" in reason


def test_mtf_bearish_rejection():
    mtf = MultiTimeframeConfluence(ema_fast=9, ema_slow=21)
    # 25 candles in steep downtrend
    klines_15m = [
        {"high": 200 - i * 2, "low": 198 - i * 2, "close": 199 - i * 2, "volume": 1000}
        for i in range(25)
    ]
    is_aligned, reason = mtf.check_higher_timeframe(klines_15m)
    assert is_aligned is False
    assert "MTF_BEARISH_REJECTION" in reason or "MTF_DOWNTREND" in reason


def test_mtf_insufficient_history_bypasses():
    mtf = MultiTimeframeConfluence()
    is_aligned, reason = mtf.check_higher_timeframe([])
    assert is_aligned is True
    assert "MTF_BYPASS" in reason
