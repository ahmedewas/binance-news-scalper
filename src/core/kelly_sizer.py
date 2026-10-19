"""Fractional Kelly Criterion dynamic position sizing engine."""
import math
from typing import Tuple


class KellySizer:
    def __init__(self, kelly_fraction: float = 0.5, default_win_loss_ratio: float = 1.33):
        self.kelly_fraction = max(0.1, min(1.0, kelly_fraction))
        self.b = default_win_loss_ratio

    def calculate_kelly_fraction(self, win_prob: float) -> float:
        """Computes conservative fractional Kelly bet size percentage."""
        p = max(0.01, min(0.99, win_prob))
        q = 1.0 - p
        raw_kelly = (p * self.b - q) / self.b
        if raw_kelly <= 0:
            return 0.0
        return round(raw_kelly * self.kelly_fraction, 4)

    def size_position(
        self,
        usdt_balance: float,
        score: float,
        min_notional: float = 5.0,
        max_position_pct: float = 0.50,
    ) -> Tuple[bool, float, str]:
        """Calculates optimal dollar size based on quantitative edge."""
        if usdt_balance < min_notional:
            return False, 0.0, f"Balance {usdt_balance:.2f} < Min {min_notional}"

        # Map score (75 to 100) to win probability (0.60 to 0.90)
        norm_score = max(0.0, min(100.0, score))
        win_prob = 0.55 + ((norm_score / 100.0) * 0.35)

        k_frac = self.calculate_kelly_fraction(win_prob)
        if k_frac <= 0:
            return False, 0.0, "Zero Kelly edge"

        target_allocation = usdt_balance * min(max_position_pct, k_frac)
        final_size = max(min_notional, round(target_allocation, 2))

        if final_size > usdt_balance:
            final_size = round(usdt_balance, 2)

        if final_size < min_notional:
            return False, 0.0, f"Size {final_size} < Min notional {min_notional}"

        return True, final_size, f"Kelly Size: ${final_size:.2f} (Prob: {win_prob*100:.1f}%)"
