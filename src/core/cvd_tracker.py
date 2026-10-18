"""Cumulative Volume Delta (CVD) and Aggressive Order Flow Tracker."""
from typing import List, Dict, Any, Tuple


class CVDTracker:
    def __init__(self, min_imbalance_ratio: float = 0.30):
        self.min_imbalance = min_imbalance_ratio

    def calculate_delta(
        self, trades: List[Dict[str, Any]]
    ) -> Tuple[float, float, float]:
        """Calculates aggressive buy volume, sell volume, and net delta."""
        buy_vol = 0.0
        sell_vol = 0.0

        for t in trades:
            vol = float(t.get("amount", 0.0))
            is_buyer_maker = t.get("is_buyer_maker", False)
            # In Binance: if buyer is maker, the aggressive taker was a SELLER
            if is_buyer_maker:
                sell_vol += vol
            else:
                buy_vol += vol

        net_delta = buy_vol - sell_vol
        total_vol = buy_vol + sell_vol
        imbalance = (net_delta / total_vol) if total_vol > 0 else 0.0
        return buy_vol, sell_vol, imbalance

    def validate_whale_pressure(
        self, trades: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """Validates whether aggressive market buying dominates to reject spoofing."""
        if not trades:
            return False, 0.0, "No trade flow data"

        buy_vol, sell_vol, imbalance = self.calculate_delta(trades)

        if imbalance >= self.min_imbalance:
            score = min(100.0, 70.0 + (imbalance * 40.0))
            return True, round(score, 2), f"Aggressive Buyers Dominating ({imbalance*100:.1f}%)"

        if imbalance < 0:
            return False, 0.0, f"Aggressive Selling Pressure ({imbalance*100:.1f}%)"

        return False, 50.0, f"Neutral Flow ({imbalance*100:.1f}%)"
