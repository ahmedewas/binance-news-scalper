"""Unit tests for Cumulative Volume Delta (CVD) order flow tracker."""
from src.core.cvd_tracker import CVDTracker


def test_cvd_buyer_dominance():
    tracker = CVDTracker(min_imbalance_ratio=0.30)
    trades = [
        {"amount": 10.0, "is_buyer_maker": False},
        {"amount": 15.0, "is_buyer_maker": False},
        {"amount": 20.0, "is_buyer_maker": False},
        {"amount": 5.0, "is_buyer_maker": True},
    ]
    valid, score, reason = tracker.validate_whale_pressure(trades)
    assert valid
    assert score >= 70.0
    assert "Aggressive Buyers Dominating" in reason


def test_cvd_seller_rejection():
    tracker = CVDTracker(min_imbalance_ratio=0.30)
    trades = [
        {"amount": 5.0, "is_buyer_maker": False},
        {"amount": 45.0, "is_buyer_maker": True},
    ]
    valid, score, reason = tracker.validate_whale_pressure(trades)
    assert not valid
    assert score == 0.0
    assert "Selling Pressure" in reason


def test_cvd_empty_trades():
    tracker = CVDTracker()
    valid, score, reason = tracker.validate_whale_pressure([])
    assert not valid
    assert "No trade flow data" in reason


def test_cvd_evaluate_order_flow_candles():
    tracker = CVDTracker()
    klines = [
        {"open": 10.0, "close": 10.5, "volume": 100.0},
        {"open": 10.5, "close": 11.0, "volume": 200.0},
        {"open": 11.0, "close": 10.8, "volume": 50.0},
    ]
    score, reason = tracker.evaluate_order_flow(klines)
    assert score > 50.0
    assert "CVD Imbalance" in reason

    score_empty, _ = tracker.evaluate_order_flow([])
    assert score_empty == 50.0
