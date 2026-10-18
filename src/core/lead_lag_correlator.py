"""Lead-Lag Cross-Asset Correlator exploiting latency between sector leaders and laggards."""
from typing import Dict, List, Optional, Tuple


SECTOR_ECOSYSTEMS: Dict[str, List[str]] = {
    "SOL/USDT": ["JUP/USDT", "RAY/USDT"],
    "FET/USDT": ["RENDER/USDT", "NEAR/USDT"],
    "BTC/USDT": ["ETH/USDT", "SOL/USDT"],
    "AVAX/USDT": ["JOE/USDT", "QI/USDT"],
}


class LeadLagCorrelator:
    def __init__(
        self,
        leader_threshold: float = 0.012,  # 1.2% leader surge
        laggard_ceiling: float = 0.004,   # laggard has not moved yet (<0.4%)
    ):
        self.leader_threshold = leader_threshold
        self.laggard_ceiling = laggard_ceiling

    def evaluate_opportunity(
        self,
        leader_symbol: str,
        leader_return: float,
        laggard_symbol: str,
        laggard_return: float,
    ) -> Tuple[bool, float, str]:
        """Calculates latency arbitrage signal between leader and follower."""
        valid_followers = SECTOR_ECOSYSTEMS.get(leader_symbol, [])
        if laggard_symbol not in valid_followers:
            return False, 0.0, "Not a correlated follower"

        if leader_return >= self.leader_threshold and laggard_return <= self.laggard_ceiling:
            edge = leader_return - laggard_return
            confidence = min(100.0, 70.0 + (edge * 1500.0))
            return True, round(confidence, 2), f"Lead-Lag Edge: +{edge*100:.2f}%"

        return False, 0.0, "No latency divergence"

    def get_followers(self, leader_symbol: str) -> List[str]:
        """Returns registered laggard assets for a given sector leader."""
        return SECTOR_ECOSYSTEMS.get(leader_symbol, [])
