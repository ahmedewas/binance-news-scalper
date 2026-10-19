"""Unit tests for PerformanceTracker."""
from src.core.performance_tracker import PerformanceTracker


def test_performance_tracker_summary():
    tracker = PerformanceTracker(initial_balance=15.0)
    summary = tracker.get_summary(current_balance=15.5)

    assert summary["initial_balance"] == 15.0
    assert summary["current_balance"] == 15.5
    assert summary["total_pnl_usd"] == 0.5
    assert summary["total_pnl_pct"] == 3.33
    assert summary["total_trades"] == 0
    assert summary["win_rate"] == 0.0


def test_performance_tracker_records_trades():
    tracker = PerformanceTracker(initial_balance=15.0)
    tracker.record_trade("BTC/USDT", 1.5, 0.075, "TRAILING_TP")
    tracker.record_trade("ETH/USDT", -0.9, -0.045, "STOP_LOSS")

    summary = tracker.get_summary(current_balance=15.03)
    assert summary["total_trades"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["win_rate"] == 50.0


def test_translate_reason():
    assert "وقف الخسارة" in PerformanceTracker.translate_reason("STOP_LOSS")
    assert "جني أرباح متحرك" in PerformanceTracker.translate_reason("TRAILING_TP")
    assert "خروج زمني" in PerformanceTracker.translate_reason("TIMEOUT_RECYCLE")
    assert "جفاف أحجام" in PerformanceTracker.translate_reason("VOLUME_DECAY_EXIT")
