"""Unit tests for Cumulative Volume Delta (CVD) order flow tracker."""
from src.core.cvd_tracker import CVDTracker


def test_cvd_buyer_dominance():
    tracker = CVDTracker(min_imbalance_ratio=0.30)
    # 5 trades: 4 aggressive buys (is_buyer_maker=False), 1 sell (is_buyer_maker=True)
    trades = [
        {"amount": 10.0, "is_buyer_maker": False},
        {"amount": 15.0, "is_buyer_maker": False},
        {"amount": 20.0, "is_buyer_maker": False},
        {"amount": 5.0, "is_buyer_maker": True},
    ]
    # Buy: 45, Sell: 5, Total: 50, Imbalance: (45-5)/50 = 0.80 (80%)
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
    # Buy: 5, Sell: 45, Total: 50, Imbalance = (5-45)/50 = -0.80 (-80%)
    valid, score, reason = tracker.validate_whale_pressure(trades)
    assert not valid
    assert score == 0.0
    assert "Selling Pressure" in reason


def test_cvd_empty_trades():
    tracker = CVDTracker()
    valid, score, reason = tracker.validate_whale_pressure([])
    assert not valid
    assert "No trade flow data" in reason
