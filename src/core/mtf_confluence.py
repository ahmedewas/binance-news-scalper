"""Multi-Timeframe Confluence Engine: Aligns 1m scalp entries with 15m institutional trend."""
from typing import List, Dict, Any, Tuple


class MultiTimeframeConfluence:
    def __init__(self, ema_fast: int = 9, ema_slow: int = 21):
        self.fast_period = ema_fast
        self.slow_period = ema_slow

    def _calculate_ema(self, values: List[float], period: int) -> float:
        if not values:
            return 0.0
        if len(values) < period:
            return sum(values) / len(values)
        multiplier = 2.0 / (period + 1.0)
        ema = sum(values[:period]) / period
        for val in values[period:]:
            ema = (val - ema) * multiplier + ema
        return ema

    def check_higher_timeframe(self, klines_15m: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Validates that 15m timeframe is in an upward or neutral accumulation regime."""
        if not klines_15m or len(klines_15m) < self.slow_period:
            return True, "MTF_BYPASS: Insufficient 15m kline history"

        closes = [float(k.get("close", 0.0)) for k in klines_15m]
        fast_ema = self._calculate_ema(closes, self.fast_period)
        slow_ema = self._calculate_ema(closes, self.slow_period)
        cur_price = closes[-1]

        # 1. Bearish Downtrend: Price is below both EMAs and Fast EMA < Slow EMA
        if cur_price < fast_ema and fast_ema < slow_ema:
            pct_below = (slow_ema - cur_price) / slow_ema
            return (
                False,
                f"MTF_BEARISH_REJECTION: 15m is in downtrend ({pct_below*100:.2f}% below EMA21)",
            )

        # 2. Check 15m candle structure: Lower Highs + Lower Lows
        if len(klines_15m) >= 3:
            highs = [float(k.get("high", 0.0)) for k in klines_15m[-3:]]
            lows = [float(k.get("low", 0.0)) for k in klines_15m[-3:]]
            if highs[2] < highs[1] < highs[0] and lows[2] < lows[1] < lows[0] and cur_price < fast_ema:
                return False, "MTF_DOWNTREND_STRUCTURE: Consecutive 15m lower-lows detected"

        # 3. Macro Multi-Hour Dump Protection (16 candles * 15m = 4 hours)
        if len(closes) >= 16:
            change_4h = (closes[-1] - closes[-16]) / closes[-16]
            if change_4h < -0.030 and cur_price < slow_ema:
                return False, f"MTF_MACRO_DUMP_PROTECTION: 4h trend is down {change_4h*100:.1f}%"

        return True, "MTF_BULLISH_CONFLUENCE: 15m trend supportive"
