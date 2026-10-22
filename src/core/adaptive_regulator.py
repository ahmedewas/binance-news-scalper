"""Market-Adaptive Score Regulator: Dynamically scales score thresholds based on BTC macro trend."""
from typing import List, Dict, Any, Tuple


class AdaptiveScoreRegulator:
    def __init__(self, base_threshold: float = 75.0, min_clamp: float = 70.0, max_clamp: float = 85.0):
        self.base_threshold = base_threshold
        self.min_clamp = min_clamp
        self.max_clamp = max_clamp

    def calculate_ema(self, values: List[float], period: int) -> float:
        if not values:
            return 0.0
        if len(values) < period:
            return sum(values) / len(values)
        k = 2.0 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = v * k + ema * (1.0 - k)
        return ema

    def evaluate_regime(self, btc_klines_15m: List[Dict[str, Any]]) -> Tuple[float, str, str]:
        """Calculates effective score threshold based on 15m BTC macro structure."""
        if not btc_klines_15m or len(btc_klines_15m) < 10:
            return self.base_threshold, "NEUTRAL", "بيانات البيتكوين غير كافية؛ الاعتماد على العتبة القياسية"

        closes = [float(k.get("close", 0.0)) for k in btc_klines_15m]
        cur_price = closes[-1]
        start_price = closes[0]

        if cur_price <= 0 or start_price <= 0:
            return self.base_threshold, "NEUTRAL", "سعر غير صالح؛ العتبة القياسية"

        ret_pct = (cur_price - start_price) / start_price
        ema9 = self.calculate_ema(closes, 9)
        ema21 = self.calculate_ema(closes, 21)

        # 1. Macro Lockout: BTC heavy dump
        if ret_pct <= -0.02 or cur_price < ema21 * 0.985:
            return 99.0, "MACRO_LOCKOUT", f"هبوط بيتكوين حاد ({ret_pct*100:.2f}%)؛ تجميد الدخول لجميع العملات"

        # 2. Bullish Regime: BTC above EMA9 & EMA21 with positive return
        if cur_price > ema9 > ema21 and ret_pct > 0.003:
            effective = max(self.min_clamp, self.base_threshold - 4.0)
            return effective, "BULLISH_MOMENTUM", f"زخم صاعد للبيتكوين (+{ret_pct*100:.2f}%)؛ خفض العتبة إلى {effective:.1f}"

        # 3. Bearish Retracement: BTC below EMA9 or negative return
        if cur_price < ema9 or ret_pct < -0.005:
            effective = min(self.max_clamp, self.base_threshold + 6.0)
            return effective, "BEARISH_DEFENSE", f"ضعف أو هبوط في البيتكوين ({ret_pct*100:.2f}%)؛ رفع العتبة دفاعياً إلى {effective:.1f}"

        # 4. Neutral / Sideways
        return self.base_threshold, "SIDEWAYS", f"سوق متذبذب مستقر؛ العتبة المعتدلة {self.base_threshold:.1f}"
