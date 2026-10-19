"""Dynamic Triple-Exit risk manager: Trailing TP, Hard SL, and Timeout."""
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

        # Check Breakeven Lock (+0.6% gain locks entry + fees)
        be_activation = position.entry_price * (1.0 + self.breakeven_trigger_pct)
        if position.highest_price >= be_activation:
            position.is_breakeven_locked = True

        # Check Multi-Stage 50% Partial Take-Profit at +1.2%
        if not position.partial_tp_done and current_price >= position.entry_price * (1.0 + self.stage1_tp_pct):
            position.partial_tp_done = True
            position.is_breakeven_locked = True
            pnl = (current_price - position.entry_price) / position.entry_price
            return True, f"PARTIAL_TP_50 (Secured 50% gain: +{pnl*100:.2f}%)", 0.5

        # 1. Stop-Loss Check (Breakeven or Hard SL)
        if position.is_breakeven_locked:
            be_price = position.entry_price * (1.0 + self.fee_coverage_pct)
            if current_price <= be_price:
                return True, "BREAKEVEN_EXIT (Locked profit with fees covered)", 1.0
        else:
            sl_price = position.entry_price * (1.0 - self.stop_loss_pct)
            if current_price <= sl_price:
                return True, f"STOP_LOSS (Price {current_price} <= SL {sl_price:.4f})", 1.0

        # 2. Trailing Take-Profit Check (For Remaining Position)
        tp_activation = position.entry_price * (1.0 + self.trailing_tp_pct)
        if position.highest_price >= tp_activation:
            trailing_stop = position.highest_price * (1.0 - self.trailing_offset_pct)
            if current_price <= trailing_stop:
                pnl = (current_price - position.entry_price) / position.entry_price
                return True, f"TRAILING_TP (PnL: +{pnl*100:.2f}%)", 1.0

        # 3. Time-Based Timeout Check
        elapsed = (now - position.entry_time).total_seconds() / 60.0
        if elapsed >= self.timeout_minutes:
            return True, f"TIMEOUT_RECYCLE (Elapsed {elapsed:.1f}m >= {self.timeout_minutes}m)", 1.0

        return False, "HOLD", 0.0
