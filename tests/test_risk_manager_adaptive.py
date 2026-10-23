"""Unit tests for Micro-Profit lock, Runner Extension, and Dormant Pruner in RiskManager."""
from datetime import datetime, timezone, timedelta
from src.core.models import Position
from src.core.risk_manager import RiskManager


def test_micro_profit_lock_at_0_3_pct():
    risk = RiskManager()
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
    )
    # Price rises to 100.32 (+0.32% >= 0.30% trigger)
    risk.evaluate_exit(pos, current_price=100.32)
    assert pos.is_breakeven_locked is True

    # When price pulls back to 100.19 (below locked stop of 100.20)
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=100.19)
    assert should_exit is True
    assert ratio == 1.0
    assert "BREAKEVEN_EXIT" in reason


def test_runner_extension_holds_at_minute_22_when_green():
    risk = RiskManager(timeout_minutes=20)
    time_22m_ago = datetime.now(timezone.utc) - timedelta(minutes=22)
    pos = Position(
        symbol="FIL/USDT", entry_price=1.000, current_price=1.004,
        amount=10.0, highest_price=1.004,
        entry_time=time_22m_ago, slot_id=1,
    )
    # Price is +0.40% in profit (> +0.25%), so runner extension gives it up to 35m
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=1.004)
    assert should_exit is False
    assert reason == "HOLD"


def test_runner_extension_exits_at_minute_36():
    risk = RiskManager(timeout_minutes=20)
    time_36m_ago = datetime.now(timezone.utc) - timedelta(minutes=36)
    pos = Position(
        symbol="FIL/USDT", entry_price=1.000, current_price=1.004,
        amount=10.0, highest_price=1.004,
        entry_time=time_36m_ago, slot_id=1,
    )
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=1.004)
    assert should_exit is True
    assert "TIMEOUT_RECYCLE" in reason


def test_dormant_pruner_recycles_at_minute_13_when_flat():
    risk = RiskManager()
    time_13m_ago = datetime.now(timezone.utc) - timedelta(minutes=13)
    pos = Position(
        symbol="DOT/USDT", entry_price=10.00, current_price=10.005,
        amount=1.0, highest_price=10.008,  # highest was only +0.08% < 0.15%
        entry_time=time_13m_ago, slot_id=1,
    )
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=10.005)
    assert should_exit is True
    assert "DORMANT_RECYCLE" in reason
