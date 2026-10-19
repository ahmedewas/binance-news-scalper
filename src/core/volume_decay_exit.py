"""Preemptive volume decay detector exiting stagnant positions before full timeout."""
from typing import List, Dict, Any, Tuple


class VolumeDecayExitDetector:
    def __init__(self, min_retention_ratio: float = 0.25, min_elapsed_minutes: float = 3.0):
        self.min_retention = min_retention_ratio
        self.min_elapsed = min_elapsed_minutes

    def check_volume_decay(
        self,
        entry_volume: float,
        recent_klines: List[Dict[str, Any]],
        elapsed_minutes: float,
        current_pnl_pct: float,
    ) -> Tuple[bool, str]:
        """Detects whether trading momentum has completely dried up to recycle capital early."""
        if elapsed_minutes < self.min_elapsed or entry_volume <= 0:
            return False, "HOLD: Elapsed time below decay threshold"

        if not recent_klines:
            return False, "HOLD: No recent klines"

        cur_vol = float(recent_klines[-1].get("volume", 0.0))
        retention = cur_vol / entry_volume

        # If volume collapsed by >75% and position is not surging, exit early
        if retention < self.min_retention and current_pnl_pct < 0.008:
            return (
                True,
                f"PREEMPTIVE_VOLUME_DECAY: Volume collapsed to {retention*100:.1f}% of entry",
            )

        return False, f"HOLD: Volume retention healthy ({retention*100:.1f}%)"
