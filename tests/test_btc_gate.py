"""Unit tests for Bitcoin Market Gate."""
from src.core.btc_gate import BitcoinMarketGate


def test_btc_gate_allows_stable_market():
    gate = BitcoinMarketGate(max_btc_drop_pct=0.004, lookback_candles=5)
    # 5 stable candles
    klines = [{"open": 65000, "close": 65020 + i * 5, "volume": 100} for i in range(5)]
    is_safe, reason = gate.evaluate(klines)
    assert is_safe is True
    assert "BTC_STABLE" in reason


def test_btc_gate_vetoes_sharp_drop():
    gate = BitcoinMarketGate(max_btc_drop_pct=0.004, lookback_candles=5)
    # BTC drops by 0.6%
    klines = [
        {"open": 65000, "close": 65000, "volume": 100},
        {"open": 64900, "close": 64800, "volume": 100},
        {"open": 64800, "close": 64700, "volume": 100},
        {"open": 64700, "close": 64650, "volume": 100},
        {"open": 64650, "close": 64600, "volume": 500},
    ]
    is_safe, reason = gate.evaluate(klines)
    assert is_safe is False
    assert "BTC_DUMP_PROTECTION" in reason


def test_btc_gate_insufficient_history():
    gate = BitcoinMarketGate()
    is_safe, reason = gate.evaluate([])
    assert is_safe is True
    assert "BTC_GATE_BYPASS" in reason
