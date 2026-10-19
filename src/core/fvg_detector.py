"""Institutional Fair Value Gap (FVG) and Liquidity Imbalance Detector."""
from typing import List, Dict, Any, Tuple


class FVGDetector:
    def __init__(self, min_gap_pct: float = 0.0015):
        self.min_gap_pct = min_gap_pct

    def detect_latest_fvg(
        self, klines: List[Dict[str, Any]]
    ) -> Tuple[bool, str, float, str]:
        """Detects whether recent 3-candle structure contains institutional FVG."""
        if len(klines) < 3:
            return False, "NONE", 0.0, "Insufficient klines"

        # Examine the most recent complete 3 candles: c0, c1, c2
        c0 = klines[-3]
        c1 = klines[-2]
        c2 = klines[-1]

        c0_high = float(c0.get("high", 0.0))
        c0_low = float(c0.get("low", 0.0))
        c2_low = float(c2.get("low", 0.0))
        c2_high = float(c2.get("high", 0.0))

        # Bullish FVG: Candle 2 Low > Candle 0 High
        if c2_low > c0_high:
            gap = (c2_low - c0_high) / c0_high if c0_high > 0 else 0.0
            if gap >= self.min_gap_pct:
                score = min(100.0, 70.0 + (gap * 5000.0))
                return True, "BULLISH_FVG", round(score, 1), f"Bullish FVG: +{gap*100:.2f}% Gap"

        # Bearish FVG: Candle 2 High < Candle 0 Low
        if c2_high < c0_low:
            gap = (c0_low - c2_high) / c0_low if c0_low > 0 else 0.0
            if gap >= self.min_gap_pct:
                score = min(100.0, 70.0 + (gap * 5000.0))
                return True, "BEARISH_FVG", round(score, 1), f"Bearish FVG: -{gap*100:.2f}% Gap"

        return False, "NONE", 0.0, "No significant FVG imbalance"
