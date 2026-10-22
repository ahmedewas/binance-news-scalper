"""Dynamic Triple-Exit risk manager: Trailing TP, Ratchet Ladder, Hard SL, and Timeout."""
from datetime import datetime, timezone
from typing import Tuple, Optional
from src.core.models import Position


class RiskManager:
    def __init__(
        self,
        trailing_tp_pct: float = 0.012,
        trailing_offset_pct: float = 0.004,
        stop_loss_pct: float = 0.009,
        timeout_minutes: int = 20,
        breakeven_trigger_pct: float = 0.006,
        fee_coverage_pct: float = 0.002,
        stage1_tp_pct: float = 0.012,
    ):
        self.trailing_tp_pct = trailing_tp_pct
        self.trailing_offset_pct = trailing_offset_pct
        self.stop_loss_pct = stop_loss_pct
        self.timeout_minutes = timeout_minutes
        self.breakeven_trigger_pct = breakeven_trigger_pct
        self.fee_coverage_pct = fee_coverage_pct
        self.stage1_tp_pct = stage1_tp_pct

    def evaluate_exit(
        self, position: Position, current_price: float, now: Optional[datetime] = None
    ) -> Tuple[bool, str, float]:
        """Evaluates whether to close (or partially close) the position (exit_ratio: 0.5 or 1.0)."""
        now = now or datetime.now(timezone.utc)
        position.current_price = current_price
        if current_price > position.highest_price:
            position.highest_price = current_price

        gain_high = (position.highest_price - position.entry_price) / position.entry_price
        if gain_high >= self.breakeven_trigger_pct:
            position.is_breakeven_locked = True

        # Check Multi-Stage 50% Partial Take-Profit at +1.2%
        if not position.partial_tp_done and current_price >= position.entry_price * (1.0 + self.stage1_tp_pct):
            pnl = (current_price - position.entry_price) / position.entry_price
            return True, f"PARTIAL_TP_50 (Secured 50% gain: +{pnl*100:.2f}%)", 0.5

        # Ratcheted Ladder Stop Level calculation
        locked_stop_pct = -self.stop_loss_pct
        if gain_high >= 0.030:
            locked_stop_pct = 0.024
        elif gain_high >= 0.020:
            locked_stop_pct = 0.015
        elif gain_high >= self.stage1_tp_pct:
            locked_stop_pct = 0.008
        elif position.is_breakeven_locked:
            locked_stop_pct = self.fee_coverage_pct

        stop_price = position.entry_price * (1.0 + locked_stop_pct)

        # Trailing Take-Profit for runners
        if position.highest_price >= position.entry_price * (1.0 + self.trailing_tp_pct):
            trailing_stop = position.highest_price * (1.0 - self.trailing_offset_pct)
            if trailing_stop > stop_price:
                stop_price = trailing_stop

        # Stop / Breakeven / Ratchet Execution
        if current_price <= stop_price:
            if position.is_breakeven_locked and stop_price > position.entry_price:
                if locked_stop_pct == self.fee_coverage_pct:
                    return True, "BREAKEVEN_EXIT (Locked profit with fees covered)", 1.0
                return True, f"TRAILING_TP / RATCHET_LADDER_TP (Secured +{locked_stop_pct*100:.1f}%)", 1.0
            if current_price <= position.highest_price * (1.0 - self.trailing_offset_pct) and position.highest_price >= position.entry_price * (1.0 + self.trailing_tp_pct):
                pnl = (current_price - position.entry_price) / position.entry_price
                return True, f"TRAILING_TP (PnL: +{pnl*100:.2f}%)", 1.0
            return True, f"STOP_LOSS (Price {current_price:.4f} <= SL {stop_price:.4f})", 1.0

        # Time-Based Timeout Check
        elapsed = (now - position.entry_time).total_seconds() / 60.0
        if elapsed >= self.timeout_minutes:
            return True, f"TIMEOUT_RECYCLE (Elapsed {elapsed:.1f}m >= {self.timeout_minutes}m)", 1.0

        return False, "HOLD", 0.0
