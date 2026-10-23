"""Unit tests for FastBacktester historical simulation and optimizer."""
import pytest
from src.core.backtest_engine import FastBacktester


def test_backtester_empty_data():
    tester = FastBacktester()
    res = tester.evaluate_performance([])
    assert res["total_trades"] == 0
    assert res["win_rate"] == 0.0


def breakout_bars():
    return [{'close': 100, 'volume': 100} for _ in range(20)] + [{'close': 101, 'volume': 2000}]


def test_ambiguous_bar_does_not_use_future_high_for_stop():
    bars = breakout_bars() + [{'open': 101, 'high': 103, 'low': 99, 'close': 102, 'volume': 100}]
    trade = FastBacktester().simulate_symbol('SOL/USDT', bars)[0]
    assert trade['exit_price'] == pytest.approx(101 * .991)
    assert trade['pnl_usd'] < 0


def test_stop_gap_fills_at_open():
    bars = breakout_bars() + [{'open': 95, 'high': 99, 'low': 94, 'close': 98, 'volume': 100}]
    assert FastBacktester().simulate_symbol('SOL/USDT', bars)[0]['exit_price'] == 95


def test_insufficient_capital_prevents_entry():
    bars = breakout_bars() + [{'close': 101, 'volume': 100}]
    assert FastBacktester(initial_capital=4, slot_size=5).simulate_symbol('SOL/USDT', bars) == []


def test_end_of_data_liquidates_remaining_position():
    bars = breakout_bars() + [{'close': 101, 'volume': 100}]
    assert FastBacktester().simulate_symbol('SOL/USDT', bars)[0]['reason'] == 'END_OF_DATA'


def test_backtester_profitable_breakout_simulation():
    tester = FastBacktester(slot_size=10.0)
    # Generate 40 synthetic candles: 20 flat then breakout +3%
    klines = [{"close": 100.0, "volume": 100.0} for _ in range(20)]
    for i in range(1, 15):
        # Surging volume and price
        klines.append({"close": 100.0 + i * 0.3, "volume": 1000.0})

    trades = tester.simulate_symbol("SOL/USDT", klines, min_score=70.0, tp_pct=0.012)
    assert len(trades) >= 1
    assert trades[0]["reason"] in ("TAKE_PROFIT", "STOP_OR_RATCHET")
    assert trades[0]["pnl_usd"] > 0

    metrics = tester.evaluate_performance(trades)
    assert metrics["wins"] >= 1
    assert metrics["net_pnl_usd"] > 0
    assert metrics["profit_factor"] >= 1.0


def test_backtester_ratchet_loss_prevention():
    tester = FastBacktester(slot_size=10.0)
    # Rises +1.5% then dumps back
    klines = [{"close": 100.0, "volume": 100.0} for _ in range(20)]
    klines.extend([
        {"close": 101.5, "volume": 2000.0},
        {"close": 100.5, "volume": 500.0},
        {"close": 98.0, "volume": 500.0},
    ])
    trades = tester.simulate_symbol("SOL/USDT", klines, min_score=70.0)
    assert len(trades) >= 1
    # Stop or Ratchet exit prevented dropping to 98.0
    assert trades[0]["exit_price"] >= 100.0
