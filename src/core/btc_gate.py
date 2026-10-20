"""Bitcoin Market Regime Gate: Shields altcoin portfolio against BTC flash crashes."""
from typing import List, Dict, Any, Tuple


class BitcoinMarketGate:
    def __init__(self, max_btc_drop_pct: float = 0.004, lookback_candles: int = 5):
        self.max_drop_pct = max_btc_drop_pct
        self.lookback = lookback_candles

    def evaluate(self, btc_klines: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Evaluates whether broader market conditions are safe for altcoin entries."""
        if not btc_klines or len(btc_klines) < self.lookback:
            return True, "BTC_GATE_BYPASS: Insufficient BTC history"

        recent = btc_klines[-self.lookback:]
        start_price = float(recent[0].get("close", 0.0))
        cur_price = float(recent[-1].get("close", 0.0))

        if start_price <= 0 or cur_price <= 0:
            return True, "BTC_GATE_BYPASS: Invalid BTC price"

        change = (cur_price - start_price) / start_price

        # 1. Hard BTC Flash Drop Protection
        if change <= -self.max_drop_pct:
            return (
                False,
                f"BTC_DUMP_PROTECTION: Bitcoin fell {change*100:.2f}% over last {self.lookback}m",
            )

        # 2. Sudden Bearish Volume Spike on latest candle
        latest = recent[-1]
        l_open = float(latest.get("open", 0.0))
        l_close = float(latest.get("close", 0.0))
        l_vol = float(latest.get("volume", 0.0))

        vols = [float(k.get("volume", 0.0)) for k in recent[:-1]]
        avg_vol = sum(vols) / len(vols) if vols else 1.0

        if l_close < l_open and (l_open - l_close) / l_open > 0.0025 and l_vol > 2.2 * avg_vol:
            return False, "BTC_BEARISH_ABSORPTION: Heavy institutional selling on BTC"

        return True, f"BTC_STABLE: Bitcoin change {change*100:+.2f}% within safe corridor"
