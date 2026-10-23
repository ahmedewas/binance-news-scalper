"""Unit tests for Liquidity Wall and Iceberg Absorption Hunter."""
from src.exchange.liquidity_walls import LiquidityWallHunter


def make_balanced_levels(base_p, step, count=10, qty=10.0):
    return [[round(base_p + i * step, 4), qty] for i in range(count)]


def test_detect_blocking_sell_wall():
    hunter = LiquidityWallHunter(wall_concentration_ratio=0.30, proximity_pct=0.006)
    bids = make_balanced_levels(99.9, -0.1, 10, 10.0)
    asks = make_balanced_levels(100.1, 0.1, 10, 5.0)
    # Inject giant ask wall at 100.3 (within +0.3%)
    asks[2] = [100.3, 150.0]  # $15,000 > 50% of depth
    ok, msg, score_adj = hunter.detect_walls(bids, asks, cur_price=100.0)
    assert ok is False
    assert "SELL_WALL_BLOCK" in msg
    assert score_adj < 0


def test_detect_supportive_bid_wall():
    hunter = LiquidityWallHunter(wall_concentration_ratio=0.30, proximity_pct=0.006)
    bids = make_balanced_levels(99.9, -0.1, 10, 5.0)
    asks = make_balanced_levels(100.1, 0.1, 10, 5.0)
    # Inject giant bid cushion at 99.8 (within -0.2%)
    bids[1] = [99.8, 150.0]  # $15,000 > 50% of depth
    ok, msg, score_adj = hunter.detect_walls(bids, asks, cur_price=100.0)
    assert ok is True
    assert "BID_WALL_CUSHION" in msg
    assert score_adj > 0


def test_normal_balanced_orderbook():
    hunter = LiquidityWallHunter()
    bids = make_balanced_levels(99.9, -0.1, 10, 10.0)
    asks = make_balanced_levels(100.1, 0.1, 10, 10.0)
    ok, msg, score_adj = hunter.detect_walls(bids, asks, cur_price=100.0)
    assert ok is True
    assert "WALLS_CLEAR" in msg
    assert score_adj == 0.0
