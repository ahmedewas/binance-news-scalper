"""Sector Leader Gate: Validates candidate entry against its 5-Pillar ecosystem leader."""
from typing import Tuple, List, Dict, Any, Optional
from src.core.ecosystem_registry import EcosystemRegistry


class SectorLeaderGate:
    def __init__(self, max_leader_drop_pct: float = 0.006, min_leader_surge_pct: float = 0.008):
        self.max_drop_pct = max_leader_drop_pct
        self.min_surge_pct = min_leader_surge_pct

    def evaluate_sector(self, symbol: str, exchange) -> Tuple[bool, str, float]:
        """Evaluates ecosystem leader momentum. Returns (is_safe, reason, bonus_score)."""
        leader = EcosystemRegistry.get_leader_for_symbol(symbol)
        if not leader or leader == symbol:
            return True, "LEADER_SELF_OR_UNTRACKED", 0.0

        try:
            klines = exchange.get_historical_klines(leader, "1m", 6)
            if not klines or len(klines) < 3:
                return True, "INSUFFICIENT_LEADER_DATA", 0.0

            first_p = float(klines[0].get("close", 0.0))
            last_p = float(klines[-1].get("close", 0.0))
            if first_p <= 0 or last_p <= 0:
                return True, "INVALID_LEADER_PRICE", 0.0

            chg = (last_p - first_p) / first_p

            # 1. Hard Sector Leader Dump Protection (e.g. SOL dumping kills JTO/PYTH)
            if chg <= -self.max_drop_pct:
                msg = f"SECTOR_LEADER_DUMP: {leader} fell {chg*100:.2f}%"
                return False, msg, 0.0

            # 2. Check for heavy bearish volume spike on leader
            latest = klines[-1]
            o, c, v = float(latest.get("open", 0)), float(latest.get("close", 0)), float(latest.get("volume", 0))
            vols = [float(k.get("volume", 0)) for k in klines[:-1]]
            avg_vol = sum(vols) / len(vols) if vols else 1.0
            if c < o and (o - c) / o > 0.003 and v > 2.0 * avg_vol:
                return False, f"SECTOR_LEADER_BEARISH_ABSORPTION: {leader} heavy sell volume", 0.0

            # 3. Sector Leader Surge Bonus (Momentum Tailwinds)
            if chg >= self.min_surge_pct:
                bonus = round(min(12.0, chg * 800.0), 1)
                return True, f"SECTOR_LEADER_SURGE: {leader} up +{chg*100:.2f}%", bonus

            return True, f"SECTOR_LEADER_STABLE: {leader} within safe corridor", 0.0
        except Exception as e:
            return True, f"SECTOR_GATE_BYPASS: {e}", 0.0
