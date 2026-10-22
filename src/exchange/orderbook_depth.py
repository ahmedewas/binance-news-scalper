"""Order Book Imbalance (OBI) Guard: Analyzes top-20 bid/ask depth before order routing."""
from typing import Dict, Any, Tuple, Optional
import requests


class OrderBookDepthGuard:
    def __init__(self, min_imbalance_ratio: float = -0.30, strict_mode: bool = False):
        self.min_imbalance = min_imbalance_ratio
        self.strict_mode = strict_mode
        self.session = requests.Session()

    def calculate_imbalance(self, bids: list, asks: list) -> Tuple[float, float, float]:
        def _vol(levels):
            total = 0.0
            for item in levels[:20]:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    try:
                        p, q = float(item[0]), float(item[1])
                        if p > 0 and q > 0:
                            total += p * q
                    except (ValueError, TypeError):
                        continue
            return total

        bid_vol, ask_vol = _vol(bids), _vol(asks)
        tot = bid_vol + ask_vol
        if tot <= 0:
            return 0.0, 0.0, 0.0
        return (bid_vol - ask_vol) / tot, bid_vol, ask_vol

    def evaluate_depth(
        self, symbol: str, depth_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, float]:
        """Evaluates whether order book microstructure has sufficient buyer support."""
        data = depth_data
        if data is None:
            clean = symbol.replace("/", "").upper()
            try:
                r = self.session.get(f"https://api.binance.com/api/v3/depth?symbol={clean}&limit=20", timeout=2)
                if r.status_code == 200:
                    data = r.json()
            except Exception:
                if self.strict_mode:
                    return False, "OBI_REJECT: Orderbook depth request timed out", 0.0
                return True, "OBI_BYPASS: Orderbook depth request timed out", 0.0

        if not data or not data.get("bids") or not data.get("asks"):
            return True, "OBI_BYPASS: Insufficient depth levels", 0.0

        imbalance, b_vol, a_vol = self.calculate_imbalance(data["bids"], data["asks"])
        if imbalance < self.min_imbalance:
            return (
                False,
                f"OBI_WALL_REJECT: Heavy sell wall (Asks ${a_vol:,.0f} vs Bids ${b_vol:,.0f} | OBI {imbalance*100:.1f}%)",
                imbalance,
            )

        return True, f"OBI_HEALTHY: Buyer support adequate (OBI: {imbalance*100:+.1f}%)", imbalance
