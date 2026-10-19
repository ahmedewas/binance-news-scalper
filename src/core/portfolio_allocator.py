"""Dynamic portfolio slot allocator with fee buffer and velocity slot unlocking."""
import math
from typing import Dict, Any, Optional, Set


class PortfolioAllocator:
    def __init__(
        self,
        min_notional: float = 5.0,
        max_slots: int = 5,
        fee_buffer: float = 0.0,
    ):
        self.min_notional = max(min_notional, 5.0)
        self.max_slots = max_slots
        self.fee_buffer = fee_buffer

    def calculate_slots(self, usdt_balance: float) -> Dict[str, Any]:
        """Calculates dynamic slots and allocation after reserving fee buffer."""
        tradable = max(0.0, usdt_balance - self.fee_buffer)
        if tradable < self.min_notional:
            return {
                "total_slots": 0,
                "slot_size": 0.0,
                "can_trade": False,
                "reason": f"Tradable {tradable:.2f} < Min {self.min_notional}",
            }

        calculated_slots = math.floor(usdt_balance / self.min_notional)
        total_slots = min(self.max_slots, max(1, calculated_slots))
        tradable = max(0.0, usdt_balance - self.fee_buffer)
        slot_size = round(max(self.min_notional, tradable / total_slots), 2)

        return {
            "total_slots": total_slots,
            "slot_size": slot_size,
            "can_trade": True,
            "reason": "OK",
        }

    def get_available_slot(
        self,
        total_slots: int,
        active_slot_ids: Set[int],
        breakeven_locked_ids: Optional[Set[int]] = None,
    ) -> int:
        """Finds next available slot. If full, recycles slot if breakeven locked."""
        for slot_id in range(1, total_slots + 1):
            if slot_id not in active_slot_ids:
                return slot_id

        # Velocity Unlock: If an active slot has zero risk (breakeven locked)
        if breakeven_locked_ids:
            for locked_id in breakeven_locked_ids:
                if locked_id in active_slot_ids:
                    return locked_id + 100  # Virtual unlocked velocity slot

        return -1
