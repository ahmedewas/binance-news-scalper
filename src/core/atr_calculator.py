"""Average True Range (ATR) calculator for dynamic volatility-adjusted targets."""
from typing import List, Dict, Any, Tuple


class ATRCalculator:
    def __init__(self, period: int = 14, tp_multiplier: float = 1.8, sl_multiplier: float = 1.0):
        self.period = period
        self.tp_mult = tp_multiplier
        self.sl_mult = sl_multiplier

    def compute_atr(self, klines: List[Dict[str, Any]]) -> float:
        """Computes true range average over lookback period."""
        if not klines or len(klines) < 2:
            return 0.0

        tr_list = []
        for i in range(1, len(klines)):
            h = float(klines[i].get("high", 0.0))
            l = float(klines[i].get("low", 0.0))
            prev_c = float(klines[i - 1].get("close", 0.0))

            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)

        if not tr_list:
            return 0.0
        sub = tr_list[-self.period:] if len(tr_list) >= self.period else tr_list
        return sum(sub) / len(sub)

    def calculate_targets(
        self, entry_price: float, klines: List[Dict[str, Any]]
    ) -> Tuple[float, float, float]:
        """Returns (dynamic_tp_pct, dynamic_sl_pct, atr_value). Clamped for safety."""
        if entry_price <= 0:
            return 0.012, 0.009, 0.0

        atr = self.compute_atr(klines)
        if atr <= 0:
            return 0.012, 0.009, 0.0

        atr_pct = atr / entry_price

        # Fast momentum scalping targets: TP clamped between +0.9% and +2.5%
        tp_pct = round(min(0.025, max(0.009, atr_pct * self.tp_mult)), 4)

        # SL clamped between -0.6% and -1.2%
        sl_pct = round(min(0.012, max(0.006, atr_pct * self.sl_mult)), 4)

        return tp_pct, sl_pct, round(atr, 6)
