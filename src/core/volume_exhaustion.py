"""Wyckoff Volume Exhaustion and Whale Absorption Detector."""
from typing import List, Dict, Any, Tuple


class VolumeExhaustionDetector:
    def __init__(self, min_wick_ratio: float = 0.40, min_vol_multiplier: float = 1.6):
        self.min_wick_ratio = min_wick_ratio
        self.min_vol_multiplier = min_vol_multiplier

    def analyze_absorption(
        self, klines: List[Dict[str, Any]]
    ) -> Tuple[bool, str, float, str]:
        """Detects whether recent price action displays Wyckoff absorption or exhaustion."""
        if len(klines) < 10:
            return False, "NEUTRAL", 0.0, "Insufficient klines"

        vols = [float(k.get("volume", 0.0)) for k in klines[-10:]]
        avg_vol = sum(vols[:-1]) / max(1, len(vols) - 1)
        cur_candle = klines[-1]
        cur_vol = float(cur_candle.get("volume", 0.0))

        high = float(cur_candle.get("high", 0.0))
        low = float(cur_candle.get("low", 0.0))
        open_p = float(cur_candle.get("open", 0.0))
        close_p = float(cur_candle.get("close", 0.0))

        candle_range = high - low
        if candle_range <= 0:
            return False, "NEUTRAL", 0.0, "Flat candle"

        vol_mult = cur_vol / max(1e-6, avg_vol)
        lower_wick = min(open_p, close_p) - low
        upper_wick = high - max(open_p, close_p)
        lower_ratio = lower_wick / candle_range
        upper_ratio = upper_wick / candle_range

        # Wyckoff Spring: Heavy volume + massive lower absorption wick
        if vol_mult >= self.min_vol_multiplier and lower_ratio >= self.min_wick_ratio:
            confidence = min(100.0, 75.0 + (lower_ratio * 30.0))
            return True, "WYCKOFF_SPRING", round(confidence, 1), f"Whale Absorption Wick ({lower_ratio*100:.1f}%)"

        # Wyckoff Upthrust (UTAD): Heavy volume + massive upper rejection wick
        if vol_mult >= self.min_vol_multiplier and upper_ratio >= self.min_wick_ratio:
            confidence = min(100.0, 75.0 + (upper_ratio * 30.0))
            return True, "WYCKOFF_UPTHRUST", round(confidence, 1), f"Distribution Upthrust ({upper_ratio*100:.1f}%)"

        return False, "NEUTRAL", 0.0, "Standard candle dynamic"
