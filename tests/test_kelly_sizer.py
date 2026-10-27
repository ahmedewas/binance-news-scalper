"""Unit tests for Fractional Kelly Criterion Dynamic Position Sizer."""
from src.core.kelly_sizer import KellySizer


def test_kelly_zero_edge():
    sizer = KellySizer()
    frac = sizer.calculate_kelly_fraction(win_prob=0.30)
    assert frac == 0.0


def test_kelly_high_edge_fraction():
    sizer = KellySizer(kelly_fraction=0.5, default_win_loss_ratio=1.33)
    # Win prob 80%: (0.80 * 1.33 - 0.20) / 1.33 = (1.064 - 0.2) / 1.33 = 0.649 -> half kelly ~ 0.32
    frac = sizer.calculate_kelly_fraction(win_prob=0.80)
    assert frac > 0.25
    assert frac < 0.40


def test_kelly_sizing_with_high_score():
    sizer = KellySizer()
    # High score 90/100 -> Kelly sizes appropriately
    ok, size, msg = sizer.size_position(usdt_balance=100.0, score=90.0, min_notional=5.0)
    assert ok
    assert size >= 5.0
    assert size <= 50.0  # Capped by max_position_pct (50%)
    assert "Kelly Size" in msg


def test_kelly_sizing_below_min_notional():
    sizer = KellySizer()
    ok, size, msg = sizer.size_position(usdt_balance=4.0, score=95.0, min_notional=5.0)
    assert not ok
    assert size == 0.0


def test_kelly_alpha_multiplier():
    sizer = KellySizer()
    # Baseline
    assert sizer.calculate_alpha_multiplier(score=75.0) == 1.0
    # High score (>=88)
    assert sizer.calculate_alpha_multiplier(score=90.0) == 1.20
    # Star coin (2+ wins, 0 losses) + High score
    star_mult = sizer.calculate_alpha_multiplier(score=90.0, symbol_wins=3, symbol_losses=0)
    assert star_mult == 1.40
    # Max cap check
    capped = sizer.calculate_alpha_multiplier(score=95.0, symbol_wins=5, symbol_losses=0, has_vector_match=True)
    assert capped == 1.50
