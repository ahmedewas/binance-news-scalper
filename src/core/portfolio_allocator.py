"""Dynamic portfolio slot allocator respecting Binance Min Notional."""
import math
from typing import Dict, Any


class PortfolioAllocator:
    def __init__(self, min_notional: float = 5.0, max_slots: int = 5):
        self.min_notional = max(min_notional, 5.0)
        self.max_slots = max_slots

    def calculate_slots(self, usdt_balance: float) -> Dict[str, Any]:
        """Calculates dynamic slots and allocation based on balance."""
        if usdt_balance < self.min_notional:
            return {
                "total_slots": 0,
                "slot_size": 0.0,
                "can_trade": False,
                "reason": f"Balance {usdt_balance:.2f} < Min {self.min_notional}",
            }

        # Calculate max possible slots of at least min_notional
        calculated_slots = math.floor(usdt_balance / self.min_notional)
        total_slots = min(self.max_slots, max(1, calculated_slots))
        slot_size = round(usdt_balance / total_slots, 2)

        return {
            "total_slots": total_slots,
            "slot_size": slot_size,
            "can_trade": True,
            "reason": "OK",
        }

    def get_available_slot(
        self, total_slots: int, active_slot_ids: set[int]
    ) -> int:
        """Finds next available slot ID (1-indexed). Returns -1 if full."""
        for slot_id in range(1, total_slots + 1):
            if slot_id not in active_slot_ids:
                return slot_id
        return -1
