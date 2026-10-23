"""Liquidity Wall and Iceberg Absorption Hunter: Identifies local depth walls within 0.5%."""
from typing import Dict, Any, Tuple, Optional, List
import requests


class LiquidityWallHunter:
    def __init__(self, wall_concentration_ratio: float = 0.30, proximity_pct: float = 0.006):
        self.concentration_thresh = wall_concentration_ratio
        self.proximity_pct = proximity_pct
        self.session = requests.Session()

    def detect_walls(self, bids: List[Any], asks: List[Any], cur_price: float) -> Tuple[bool, str, float]:
        """Detects whether nearby liquidity contains a blocking sell wall or strong bid cushion."""
        if not bids or not asks or cur_price <= 0:
            return True, "WALLS_BYPASS: Insufficient depth", 0.0

        def parse(levels):
            res = []
            for item in levels[:20]:
                try:
                    p, q = float(item[0]), float(item[1])
                    if p > 0 and q > 0:
                        res.append((p, p * q))
                except (ValueError, TypeError):
                    continue
            return res

        b_parsed, a_parsed = parse(bids), parse(asks)
        tot_b = sum(v for _, v in b_parsed)
        tot_a = sum(v for _, v in a_parsed)

        if tot_b <= 0 or tot_a <= 0:
            return True, "WALLS_BYPASS: Zero notional depth", 0.0

        # 1. Blocking Ask Wall: Massive sell order within +0.6%
        for p, notional in a_parsed:
            dist = (p - cur_price) / cur_price
            if 0 < dist <= self.proximity_pct and (notional / tot_a) >= self.concentration_thresh:
                pct_share = (notional / tot_a) * 100.0
                return False, f"SELL_WALL_BLOCK: Giant ask wall (${notional:,.0f}, {pct_share:.0f}% of depth) at {p:.4f}", -15.0

        # 2. Supportive Bid Wall: Massive bid cushion within -0.4%
        for p, notional in b_parsed:
            dist = (cur_price - p) / cur_price
            if 0 < dist <= (self.proximity_pct * 0.75) and (notional / tot_b) >= self.concentration_thresh:
                pct_share = (notional / tot_b) * 100.0
                return True, f"BID_WALL_CUSHION: Institutional bid cushion (${notional:,.0f}, {pct_share:.0f}% of depth) at {p:.4f}", 8.0

        return True, "WALLS_CLEAR: No abnormal wall concentrations", 0.0

    def evaluate_live(self, symbol: str, cur_price: float, depth_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, float]:
        data = depth_data
        if data is None:
            clean = symbol.replace("/", "").upper()
            try:
                r = self.session.get(f"https://api.binance.com/api/v3/depth?symbol={clean}&limit=20", timeout=2)
                if r.status_code == 200:
                    data = r.json()
            except Exception:
                return True, "WALLS_BYPASS: Live depth request timeout", 0.0

        if not data:
            return True, "WALLS_BYPASS: No depth data", 0.0
        return self.detect_walls(data.get("bids", []), data.get("asks", []), cur_price)
