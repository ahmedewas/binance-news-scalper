"""Unit tests for Dynamic Triple-Exit Risk Manager."""
from datetime import datetime, timezone, timedelta
from src.core.models import Position
from src.core.risk_manager import RiskManager


def test_hard_stop_loss_trigger():
    risk = RiskManager(stop_loss_pct=0.009)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
    )
    # Price drops to 99.0 (-1.0%, which is below -0.9% SL)
    should_exit, reason = risk.evaluate_exit(pos, current_price=99.0)
    assert should_exit
    assert "STOP_LOSS" in reason


def test_trailing_take_profit_trigger():
    risk = RiskManager(trailing_tp_pct=0.012, trailing_offset_pct=0.004)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
    )
    # Price rallies to 102.5 (+2.5%), activating trailing stop
    risk.evaluate_exit(pos, current_price=102.5)
    assert pos.highest_price == 102.5

    # Price pulls back by 0.5% to 101.9 (below trailing offset of 0.4%)
    should_exit, reason = risk.evaluate_exit(pos, current_price=101.9)
    assert should_exit
    assert "TRAILING_TP" in reason


def test_timeout_recycle_trigger():
    risk = RiskManager(timeout_minutes=20)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=25)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.2,
        amount=1.0, highest_price=100.3,
        entry_time=old_time, slot_id=1,
    )
    should_exit, reason = risk.evaluate_exit(pos, current_price=100.2)
    assert should_exit
    assert "TIMEOUT_RECYCLE" in reason


def test_normal_hold():
    risk = RiskManager()
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
    )
    should_exit, reason = risk.evaluate_exit(pos, current_price=100.5)
    assert not should_exit
    assert reason == "HOLD"
