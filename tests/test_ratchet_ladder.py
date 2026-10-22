"""Unit tests for Ratcheted Ladder Profit Lock in RiskManager."""
from datetime import datetime, timezone
import pytest
from src.core.models import Position
from src.core.risk_manager import RiskManager


def test_ratchet_ladder_tier_2_lock():
    risk = RiskManager()
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
        partial_tp_done=True,
    )
    # Price reached +1.5% (Tier 2: >= 1.2% locks +0.8%)
    risk.evaluate_exit(pos, current_price=101.5)
    assert pos.highest_price == 101.5

    # Retrace to 100.7 (below locked stop of 100.8)
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=100.7)
    assert should_exit is True
    assert ratio == 1.0
    assert "RATCHET_LADDER_TP" in reason
    assert "0.8%" in reason


def test_ratchet_ladder_tier_3_lock():
    risk = RiskManager()
    pos = Position(
        symbol="SOL/USDT", entry_price=100.0, current_price=100.0,
        amount=1.0, highest_price=100.0,
        entry_time=datetime.now(timezone.utc), slot_id=1,
        partial_tp_done=True,
    )
    # Price reached +2.2% (Tier 3: >= 2.0% locks +1.5%)
    risk.evaluate_exit(pos, current_price=102.2)

    # Retrace to 101.4 (below locked stop of 101.5)
    should_exit, reason, ratio = risk.evaluate_exit(pos, current_price=101.4)
    assert should_exit is True
    assert "RATCHET_LADDER_TP" in reason
    assert "1.5%" in reason
