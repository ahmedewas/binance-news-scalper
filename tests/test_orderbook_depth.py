"""Unit tests for OrderBookDepthGuard microstructural depth analysis."""
import pytest
from src.exchange.orderbook_depth import OrderBookDepthGuard


def test_orderbook_depth_healthy_buyers():
    guard = OrderBookDepthGuard(min_imbalance_ratio=-0.30)
    # Bids total: $20,000, Asks total: $10,000 (Imbalance: +0.33)
    depth = {
        "bids": [["100.0", "100.0"], ["99.5", "100.0"]],
        "asks": [["100.5", "50.0"], ["101.0", "50.0"]],
    }
    safe, msg, imb = guard.evaluate_depth("SOL/USDT", depth_data=depth)
    assert safe is True
    assert "OBI_HEALTHY" in msg
    assert imb > 0.0


def test_orderbook_depth_heavy_sell_wall_rejection():
    guard = OrderBookDepthGuard(min_imbalance_ratio=-0.30)
    # Bids total: $2,000, Asks total: $10,000 (Imbalance: (2-10)/12 = -0.66)
    depth = {
        "bids": [["100.0", "20.0"]],
        "asks": [["100.5", "100.0"]],
    }
    safe, msg, imb = guard.evaluate_depth("SOL/USDT", depth_data=depth)
    assert safe is False
    assert "OBI_WALL_REJECT" in msg
    assert imb < -0.30


def test_orderbook_depth_empty_data_bypass():
    guard = OrderBookDepthGuard()
    safe, msg, imb = guard.evaluate_depth("SOL/USDT", depth_data={"bids": [], "asks": []})
    assert safe is True
    assert "OBI_BYPASS" in msg
    assert imb == 0.0
