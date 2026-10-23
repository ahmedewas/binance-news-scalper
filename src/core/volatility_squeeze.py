"""TTM Volatility Squeeze Engine: Detects Bollinger Band compression inside Keltner Channels."""
import math
from typing import List, Dict, Any, Tuple


class VolatilitySqueezeDetector:
    def __init__(self, bb_period: int = 20, bb_mult: float = 2.0, kc_period: int = 20, kc_mult: float = 1.5):
        self.bb_period = bb_period
        self.bb_mult = bb_mult
        self.kc_period = kc_period
        self.kc_mult = kc_mult

    def _calc_atr(self, klines: List[Dict[str, Any]], period: int) -> float:
        trs = []
        for i in range(1, len(klines)):
            h, l, prev_c = float(klines[i].get("high", 0)), float(klines[i].get("low", 0)), float(klines[i - 1].get("close", 0))
            trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
        sub = trs[-period:] if len(trs) >= period else trs
        return sum(sub) / len(sub) if sub else 0.0

    def evaluate(self, klines: List[Dict[str, Any]]) -> Tuple[bool, bool, float, str]:
        """Returns (is_in_squeeze, is_fired_bullish, momentum, description)."""
        min_bars = max(self.bb_period, self.kc_period) + 2
        if not klines or len(klines) < min_bars:
            return False, False, 0.0, "INSUFFICIENT_BARS"

        closes = [float(k.get("close", 0.0)) for k in klines]
        recent_c = closes[-self.bb_period:]
        sma = sum(recent_c) / len(recent_c)
        var = sum((c - sma) ** 2 for c in recent_c) / len(recent_c)
        std = math.sqrt(var)

        bb_up = sma + (self.bb_mult * std)
        bb_low = sma - (self.bb_mult * std)

        atr = self._calc_atr(klines, self.kc_period)
        kc_up = sma + (self.kc_mult * atr)
        kc_low = sma - (self.kc_mult * atr)

        # Squeeze condition: Bollinger Bands inside Keltner Channel
        is_squeezed = (bb_up < kc_up) and (bb_low > kc_low)

        # Check previous bar squeeze condition for "Fire" event
        prev_recent_c = closes[-(self.bb_period + 1):-1]
        prev_sma = sum(prev_recent_c) / len(prev_recent_c)
        prev_std = math.sqrt(sum((c - prev_sma) ** 2 for c in prev_recent_c) / len(prev_recent_c))
        prev_bb_up = prev_sma + (self.bb_mult * prev_std)
        prev_bb_low = prev_sma - (self.bb_mult * prev_std)
        prev_atr = self._calc_atr(klines[:-1], self.kc_period)
        prev_squeezed = (prev_bb_up < prev_sma + self.kc_mult * prev_atr) and (prev_bb_low > prev_sma - self.kc_mult * prev_atr)

        # Momentum calculation: difference of close vs midpoint of Donchian and SMA
        highs_20 = [float(k.get("high", 0.0)) for k in klines[-self.bb_period:]]
        lows_20 = [float(k.get("low", 0.0)) for k in klines[-self.bb_period:]]
        donchian_mid = (max(highs_20) + min(lows_20)) / 2.0
        delta = closes[-1] - ((donchian_mid + sma) / 2.0)
        mom = (delta / closes[-1]) * 1000.0 if closes[-1] > 0 else 0.0

        is_fired_bullish = prev_squeezed and not is_squeezed and mom > 0.0

        if is_fired_bullish:
            return False, True, round(mom, 2), f"SQUEEZE_FIRED_BULLISH: Momentum +{mom:.1f}"
        if is_squeezed:
            return True, False, round(mom, 2), f"IN_SQUEEZE_COMPRESSION: Energy Building (Mom {mom:+.1f})"
        return False, False, round(mom, 2), f"NO_SQUEEZE: Normal (Mom {mom:+.1f})"
