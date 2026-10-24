"""Counterfactual Shadow Engine: Runs 3 parallel virtual strategies to minimize regret."""
import time
from typing import Dict, Any, Tuple, Optional


class ShadowPosition:
    def __init__(self, name: str, entry_price: float, tp_pct: float, sl_pct: float, timeout_min: float):
        self.name = name
        self.entry_price = entry_price
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.timeout_sec = timeout_min * 60.0
        self.start_time = time.time()
        self.is_closed = False
        self.final_pnl_pct = 0.0
        self.exit_reason = "ACTIVE"

    def update(self, current_price: float, now: Optional[float] = None) -> bool:
        if self.is_closed:
            return True
        now = now or time.time()
        pnl = (current_price - self.entry_price) / self.entry_price
        elapsed = now - self.start_time

        if pnl >= self.tp_pct:
            self.final_pnl_pct = self.tp_pct - 0.002
            self.exit_reason = "SHADOW_TP"
            self.is_closed = True
        elif pnl <= -self.sl_pct:
            self.final_pnl_pct = -self.sl_pct - 0.002
            self.exit_reason = "SHADOW_SL"
            self.is_closed = True
        elif elapsed >= self.timeout_sec:
            self.final_pnl_pct = pnl - 0.002
            self.exit_reason = "SHADOW_TIMEOUT"
            self.is_closed = True
        return self.is_closed


class ShadowEngine:
    def __init__(self):
        # Maps symbol -> Dict[str, ShadowPosition]
        self.active_shadows: Dict[str, Dict[str, ShadowPosition]] = {}

    def spawn_shadows(self, symbol: str, entry_price: float) -> None:
        """Spawns 3 counterfactual variants for an active symbol."""
        self.active_shadows[symbol] = {
            "SCALP_FAST": ShadowPosition("SCALP_FAST", entry_price, 0.009, 0.005, 5.0),
            "MOMENTUM_MID": ShadowPosition("MOMENTUM_MID", entry_price, 0.014, 0.007, 12.0),
            "RUNNER_DEEP": ShadowPosition("RUNNER_DEEP", entry_price, 0.022, 0.009, 20.0),
        }

    def on_tick(self, symbol: str, current_price: float, now: Optional[float] = None) -> None:
        """Updates all shadow variants for symbol."""
        if symbol in self.active_shadows:
            for shadow in self.active_shadows[symbol].values():
                shadow.update(current_price, now)

    def evaluate_regret(self, symbol: str, actual_pnl_pct: float) -> Tuple[str, float, Dict[str, float]]:
        """Calculates regret = max(shadow_pnl) - actual_pnl and returns best strategy."""
        variants = self.active_shadows.pop(symbol, {})
        if not variants:
            return "NO_SHADOW", 0.0, {}

        pnls = {name: round(pos.final_pnl_pct, 4) for name, pos in variants.items()}
        best_name, best_pnl = max(pnls.items(), key=lambda item: item[1])
        regret = round(max(0.0, best_pnl - actual_pnl_pct), 4)
        return best_name, regret, pnls
