"""Symbol Cooldown Manager: Prevents over-trading and hyperactive churn on the same asset."""
import time
from typing import Dict, Tuple


class CooldownManager:
    def __init__(self, default_cooldown_minutes: float = 15.0):
        self.default_cooldown_secs = default_cooldown_minutes * 60.0
        self._cooldowns: Dict[str, float] = {}

    def set_cooldown(self, symbol: str, custom_minutes: float = None) -> None:
        """Sets a cooldown timestamp for the specified asset."""
        secs = (custom_minutes * 60.0) if custom_minutes is not None else self.default_cooldown_secs
        self._cooldowns[symbol] = time.time() + secs

    def is_in_cooldown(self, symbol: str) -> Tuple[bool, float]:
        """Returns (is_cooling_down, remaining_minutes)."""
        now = time.time()
        expiry = self._cooldowns.get(symbol, 0.0)
        if now < expiry:
            remaining = round((expiry - now) / 60.0, 1)
            return True, remaining
        if symbol in self._cooldowns:
            del self._cooldowns[symbol]
        return False, 0.0

    def clear(self) -> None:
        self._cooldowns.clear()
