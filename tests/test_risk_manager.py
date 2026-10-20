"""Unit tests for Dynamic Multi-Stage Triple-Exit Risk Manager."""
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
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=99.0)
    assert should_exit
    assert ratio == 1.0
    assert "STOP_LOSS" in reason


def test_partial_take_profit_50_pct():
    risk = RiskManager(stage1_tp_pct=0.012)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=2.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
    )
    # Price rises to 101.3 (+1.3% >= 1.2% stage1 TP)
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=101.3)
    assert should_exit
    assert ratio == 0.5  # Sells 50%
    assert not pos.partial_tp_done  # Commit only after an execution fill
    assert pos.is_breakeven_locked
    assert "PARTIAL_TP_50" in reason


def test_trailing_take_profit_trigger():
    risk = RiskManager(trailing_tp_pct=0.012, trailing_offset_pct=0.004)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
        partial_tp_done=True,  # already took partial, riding trailing
    )
    risk.evaluate_exit(pos, current_price=102.5)
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=101.9)
    assert should_exit
    assert ratio == 1.0
    assert "TRAILING_TP" in reason


def test_timeout_recycle_trigger():
    risk = RiskManager(timeout_minutes=20)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=25)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.2,
        amount=1.0, highest_price=100.3,
        entry_time=old_time, slot_id=1,
    )
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=100.2)
    assert should_exit
    assert ratio == 1.0
    assert "TIMEOUT_RECYCLE" in reason


def test_breakeven_lock_activation_and_safe_exit():
    risk = RiskManager(breakeven_trigger_pct=0.006, fee_coverage_pct=0.002)
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
    )
    risk.evaluate_exit(pos, current_price=100.7)
    assert pos.is_breakeven_locked
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=100.1)
    assert should_exit
    assert ratio == 1.0
    assert "BREAKEVEN_EXIT" in reason
