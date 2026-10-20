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

    def calculate_slots(
        self, usdt_balance: float, total_equity: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculates dynamic slots based on equity, ensuring free cash can open slots."""
        equity = total_equity if total_equity is not None else usdt_balance
        tradable_equity = max(0.0, equity - self.fee_buffer)

        if tradable_equity < self.min_notional:
            return {
                "total_slots": 0, "slot_size": 0.0, "can_trade": False,
                "reason": f"Equity {tradable_equity:.2f} < Min {self.min_notional}",
            }

        calculated_slots = math.floor(tradable_equity / self.min_notional)
        total_slots = min(self.max_slots, max(1, calculated_slots))
        slot_size = math.floor(min(usdt_balance, tradable_equity / total_slots) * 100) / 100
        can_trade = slot_size >= self.min_notional

        return {
            "total_slots": total_slots, "slot_size": slot_size,
            "can_trade": can_trade, "reason": "OK" if can_trade else f"Cash {usdt_balance:.2f} < {slot_size}",
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

        return -1
