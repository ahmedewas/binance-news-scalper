"""Anti-Slippage Execution Shield: Protects orders from front-running and spread spikes."""
from typing import Tuple


class SlippageGuard:
    def __init__(self, max_buy_slippage_pct: float = 0.0025, max_sell_slippage_pct: float = 0.0035):
        self.max_buy_slip = max_buy_slippage_pct
        self.max_sell_slip = max_sell_slippage_pct

    def validate_buy_slippage(
        self, symbol: str, signal_price: float, current_price: float
    ) -> Tuple[bool, str, float]:
        """Ensures market buy order has not suffered adverse spread slippage before submission."""
        if signal_price <= 0 or current_price <= 0:
            return True, "SLIPPAGE_BYPASS: Invalid reference prices", 0.0

        slippage = (current_price - signal_price) / signal_price

        # Adverse price jump: price moved higher than expected
        if slippage > self.max_buy_slip:
            return (
                False,
                f"SLIPPAGE_ABORT: Price jumped {slippage*100:+.2f}% (> +{self.max_buy_slip*100:.2f}%)",
                slippage,
            )

        return True, f"SLIPPAGE_OK: Slippage {slippage*100:+.2f}% within safe tolerance", slippage

    def validate_sell_slippage(
        self, symbol: str, expected_price: float, current_price: float
    ) -> Tuple[bool, str, float]:
        """Ensures market sell execution does not dump into an evaporated bid book."""
        if expected_price <= 0 or current_price <= 0:
            return True, "SLIPPAGE_BYPASS: Invalid reference prices", 0.0

        slippage = (expected_price - current_price) / expected_price

        if slippage > self.max_sell_slip:
            return (
                False,
                f"SELL_SLIPPAGE_ABORT: Bids dropped {slippage*100:.2f}% below expected target",
                slippage,
            )

        return True, "SLIPPAGE_OK", slippage
