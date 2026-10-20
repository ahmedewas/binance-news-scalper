"""Preemptive volume decay detector exiting stagnant positions before full timeout."""
from typing import List, Dict, Any, Tuple


class VolumeDecayExitDetector:
    def __init__(self, min_retention_ratio: float = 0.25, min_elapsed_minutes: float = 5.0):
        self.min_retention = min_retention_ratio
        self.min_elapsed = min_elapsed_minutes

    def check_volume_decay(
        self,
        entry_volume: float,
        recent_klines: List[Dict[str, Any]],
        elapsed_minutes: float,
        current_pnl_pct: float,
    ) -> Tuple[bool, str]:
        """Detects whether trading momentum has completely dried up after generous lifespan."""
        if elapsed_minutes < self.min_elapsed or entry_volume <= 0:
            return False, "HOLD: Elapsed time below decay threshold"

        if len(recent_klines) < 3:
            return False, "HOLD: No recent klines"

        # Require three complete low-volume bars, not the first seconds of a new bar.
        cur_vol = max(float(k.get("volume", 0.0)) for k in recent_klines[-3:])
        retention = cur_vol / entry_volume

        # Only exit if volume collapsed by >90% AND position is not surging after generous lifespan
        if retention < self.min_retention and current_pnl_pct < 0.005:
            return (
                True,
                f"PREEMPTIVE_VOLUME_DECAY: Volume collapsed to {retention*100:.1f}% after {elapsed_minutes:.1f}m",
            )

        return False, f"HOLD: Volume retention healthy ({retention*100:.1f}%)"
