"""Market Maker Inventory Depletion Frontrun Detector."""
from typing import List, Tuple


class MarketMakerInventoryDetector:
    def __init__(self, min_depletion_ratio: float = 2.2):
        self.min_ratio = min_depletion_ratio

    def evaluate_orderbook_depletion(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        depth_levels: int = 5,
    ) -> Tuple[bool, float, str]:
        """Detects whether ask inventory has been stripped, forcing MM upward repricing."""
        if not bids or not asks:
            return False, 0.0, "Empty orderbook depth"

        top_bids = bids[:depth_levels]
        top_asks = asks[:depth_levels]

        bid_liquidity = sum(p * v for p, v in top_bids)
        ask_liquidity = sum(p * v for p, v in top_asks)

        if ask_liquidity <= 0:
            return True, 100.0, "Complete Ask Void: MM forced upward repricing"

        depletion_ratio = bid_liquidity / ask_liquidity

        if depletion_ratio >= self.min_ratio:
            edge = min(100.0, 70.0 + (depletion_ratio * 6.0))
            return (
                True,
                round(edge, 1),
                f"MM Ask Inventory Depleted ({depletion_ratio:.2f}x Bid/Ask Wall)",
            )

        return False, 0.0, f"Balanced Depth Ratio: {depletion_ratio:.2f}x"
