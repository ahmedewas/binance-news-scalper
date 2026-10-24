"""Unit tests for Institutional Sniper Risk Manager: Breakeven lock and 60-90m horizon."""
from datetime import datetime, timezone, timedelta
from src.core.models import Position
from src.core.risk_manager import RiskManager


def test_breakeven_lock_at_0_9_pct():
    risk = RiskManager(breakeven_trigger_pct=0.009, fee_coverage_pct=0.003)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
    )
    # Price rises to 101.0 (+1.0% >= 0.9% trigger)
    risk.evaluate_exit(pos, current_price=101.0)
    assert pos.is_breakeven_locked is True

    # When price pulls back to 100.29 (below locked stop of 100.30)
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=100.29)
    assert should_exit is True
    assert ratio == 1.0
    assert "BREAKEVEN_EXIT" in reason


def test_runner_extension_holds_at_minute_65_when_green():
    risk = RiskManager(timeout_minutes=60)
    time_65m_ago = datetime.now(timezone.utc) - timedelta(minutes=65)
    pos = Position(
        symbol="FIL/USDT", entry_price=1.000, current_price=1.006,
        amount=10.0, highest_price=1.006,
        entry_time=time_65m_ago, slot_id=1,
    )
    # Price is +0.60% in profit (> +0.50%), runner extension holds up to 90m
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=1.006)
    assert should_exit is False
    assert reason == "HOLD"


def test_runner_extension_exits_at_minute_92():
    risk = RiskManager(timeout_minutes=60)
    time_92m_ago = datetime.now(timezone.utc) - timedelta(minutes=92)
    pos = Position(
        symbol="FIL/USDT", entry_price=1.000, current_price=1.006,
        amount=10.0, highest_price=1.006,
        entry_time=time_92m_ago, slot_id=1,
    )
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=1.006)
    assert should_exit is True
    assert "TIMEOUT_RECYCLE" in reason


def test_standard_timeout_exits_at_minute_61_when_flat():
    risk = RiskManager(timeout_minutes=60)
    time_61m_ago = datetime.now(timezone.utc) - timedelta(minutes=61)
    pos = Position(
        symbol="DOT/USDT", entry_price=10.00, current_price=10.01,
        amount=1.0, highest_price=10.02,
        entry_time=time_61m_ago, slot_id=1,
    )
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=10.01)
    assert should_exit is True
    assert "TIMEOUT_RECYCLE" in reason
