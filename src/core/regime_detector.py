"""Wyckoff and quantitative market phase detector."""
from typing import List, Dict, Any, Tuple
from src.core.models import MarketPhase


class MarketRegimeDetector:
    @staticmethod
    def _calculate_ema(prices: List[float], period: int) -> float:
        if not prices:
            return 0.0
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = (p - ema) * multiplier + ema
        return ema

    def detect_phase(
        self, klines: List[Dict[str, Any]]
    ) -> Tuple[MarketPhase, float]:
        """Detects market phase and computes confidence score (0-100)."""
        if len(klines) < 30:
            return MarketPhase.ACCUMULATION, 50.0

        closes = [float(k["close"]) for k in klines]
        ema_fast = self._calculate_ema(closes[-15:], 10)
        ema_slow = self._calculate_ema(closes[-30:], 25)
        current_close = closes[-1]
        prev_close = closes[-2]

        pct_diff = (current_close - ema_slow) / ema_slow if ema_slow else 0.0

        if ema_fast > ema_slow and current_close > ema_fast:
            score = min(100.0, 75.0 + max(0.0, pct_diff * 500))
            return MarketPhase.MARKUP, score

        if ema_fast < ema_slow and current_close < ema_fast:
            score = min(100.0, 80.0 + abs(pct_diff * 500))
            return MarketPhase.MARKDOWN, score

        if current_close < prev_close and pct_diff > 0.03:
            return MarketPhase.DISTRIBUTION, 70.0

        return MarketPhase.ACCUMULATION, 60.0
