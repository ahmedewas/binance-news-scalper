"""Hurst Exponent Chaos and Fractal Market Memory Filter."""
import math
from typing import List, Tuple


class HurstFilter:
    def __init__(self, min_trending_hurst: float = 0.52):
        self.min_hurst = min_trending_hurst

    def calculate_hurst(self, prices: List[float]) -> float:
        """Estimates the Hurst Exponent using simplified log-range variance."""
        n = len(prices)
        if n < 20:
            return 0.50

        # Calculate log returns
        returns = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, n)
            if prices[i - 1] > 0 and prices[i] > 0
        ]
        if len(returns) < 15:
            return 0.50

        mean_ret = sum(returns) / len(returns)
        deviations = [r - mean_ret for r in returns]
        cum_dev = []
        c = 0.0
        for d in deviations:
            c += d
            cum_dev.append(c)

        r = max(cum_dev) - min(cum_dev)
        variance = sum(d ** 2 for d in deviations) / len(deviations)
        s = math.sqrt(variance) if variance > 1e-12 else 1e-6

        rs = r / s if s > 0 else 1.0
        if rs <= 0 or n <= 1:
            return 0.50

        # Hurst H = log(R/S) / log(N)
        hurst = math.log(max(1e-4, rs)) / math.log(n)
        return round(max(0.0, min(1.0, hurst)), 3)

    def validate_market_regime(
        self, prices: List[float]
    ) -> Tuple[bool, float, str]:
        """Filters out chaotic Brownian noise and accepts only persistent trending states."""
        h = self.calculate_hurst(prices)
        if h >= self.min_hurst:
            confidence = min(100.0, (h - 0.50) * 200.0 + 50.0)
            return True, round(confidence, 1), f"Persistent Trend (Hurst: {h:.3f} > 0.5)"

        if h <= 0.45:
            return False, 0.0, f"Chaos Noise Rejected (Anti-persistent Hurst: {h:.3f})"

        return False, 20.0, f"Random Walk / Brownian Motion (Hurst: {h:.3f})"
