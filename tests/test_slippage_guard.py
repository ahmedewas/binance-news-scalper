"""Unit tests for SlippageGuard anti-slippage execution shield."""
import pytest
from src.exchange.slippage_guard import SlippageGuard


def test_buy_slippage_within_tolerance():
    guard = SlippageGuard(max_buy_slippage_pct=0.0025)
    # Price moved up 0.1% (within 0.25% limit)
    ok, msg, slip = guard.validate_buy_slippage("SOL/USDT", 100.0, 100.10)
    assert ok is True
    assert "SLIPPAGE_OK" in msg
    assert slip == pytest.approx(0.001)


def test_buy_slippage_exceeds_tolerance():
    guard = SlippageGuard(max_buy_slippage_pct=0.0025)
    # Price jumped 0.5% (exceeds 0.25% limit)
    ok, msg, slip = guard.validate_buy_slippage("SOL/USDT", 100.0, 100.50)
    assert ok is False
    assert "SLIPPAGE_ABORT" in msg
    assert slip == pytest.approx(0.005)


def test_sell_slippage_protection():
    guard = SlippageGuard(max_sell_slippage_pct=0.0035)
    # Price dropped 0.2% on sell (within 0.35% tolerance)
    ok, msg, slip = guard.validate_sell_slippage("SOL/USDT", 100.0, 99.80)
    assert ok is True
    assert "SLIPPAGE_OK" in msg

    # Price dropped 0.6% on sell (exceeds 0.35% tolerance)
    ok, msg, slip = guard.validate_sell_slippage("SOL/USDT", 100.0, 99.40)
    assert ok is False
    assert "SELL_SLIPPAGE_ABORT" in msg


def test_invalid_prices_bypass():
    guard = SlippageGuard()
    ok, msg, _ = guard.validate_buy_slippage("SOL/USDT", 0.0, 100.0)
    assert ok is True
    assert "SLIPPAGE_BYPASS" in msg

    ok, msg, _ = guard.validate_sell_slippage("SOL/USDT", 100.0, -1.0)
    assert ok is True
    assert "SLIPPAGE_BYPASS" in msg
