"""Binance Order Precision Sanitizer: Normalizes quantities and price ticks to exchange rules."""
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any


class PrecisionFormatter:
    @staticmethod
    def round_down_step(amount: float, step_size: float) -> float:
        """Truncates quantity to exact step size without rounding up into deficit."""
        if step_size <= 0:
            return amount
        d_amt = Decimal(str(amount))
        d_step = Decimal(str(step_size))
        steps = (d_amt / d_step).quantize(Decimal("1"), rounding=ROUND_DOWN)
        return float(steps * d_step)

    @staticmethod
    def sanitize_amount(symbol: str, raw_amount: float, market_rules: Dict[str, Any] = None) -> float:
        """Sanitizes order amount according to LOT_SIZE stepSize rules."""
        if raw_amount <= 0:
            return 0.0
        rules = market_rules or {}
        step = rules.get("step_size", rules.get("min_amount", 0.0))
        if step > 0:
            return PrecisionFormatter.round_down_step(raw_amount, step)
        return round(raw_amount, 6)

    @staticmethod
    def is_notional_valid(symbol: str, price: float, amount: float, min_notional: float = 5.0) -> bool:
        """Verifies order total cost satisfies Binance minimum notional filter ($5 USDT)."""
        return (price * amount) >= (min_notional * 0.999)
