"""Unit tests for Market Maker Inventory Depletion Detector."""
from src.core.mm_inventory_frontrun import MarketMakerInventoryDetector


def test_ask_depletion_frontrun_trigger():
    detector = MarketMakerInventoryDetector(min_depletion_ratio=2.2)
    # Massive bids wall vs thin depleted asks
    bids = [(10.0, 500.0), (9.9, 800.0), (9.8, 1200.0)]
    asks = [(10.1, 50.0), (10.2, 80.0), (10.3, 100.0)]
    is_depleted, score, reason = detector.evaluate_orderbook_depletion(bids, asks)
    assert is_depleted
    assert score >= 70.0
    assert "Ask Inventory Depleted" in reason


def test_balanced_depth_rejection():
    detector = MarketMakerInventoryDetector(min_depletion_ratio=2.2)
    bids = [(10.0, 100.0), (9.9, 100.0)]
    asks = [(10.1, 100.0), (10.2, 100.0)]
    is_depleted, score, reason = detector.evaluate_orderbook_depletion(bids, asks)
    assert not is_depleted
    assert "Balanced Depth" in reason


def test_empty_depth():
    detector = MarketMakerInventoryDetector()
    is_depleted, score, reason = detector.evaluate_orderbook_depletion([], [])
    assert not is_depleted
    assert "Empty" in reason
