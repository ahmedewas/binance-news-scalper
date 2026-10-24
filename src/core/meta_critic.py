"""Meta-Critic Reflection Engine: Synthesizes trade logs into dynamic heuristics & blacklists."""
import time
from typing import List, Dict, Any, Tuple, Set


class MetaCritic:
    def __init__(self, penalty_duration_sec: float = 3600.0):
        self.penalty_duration = penalty_duration_sec
        # Maps symbol -> penalty_until_timestamp
        self.penalized_symbols: Dict[str, float] = {}
        self.last_reflection_summary = "INITIALIZED"

    def reflect_on_history(self, trades: List[Dict[str, Any]], now: float = None) -> str:
        """Analyzes recent trades to detect consecutive loss symbols and apply penalties."""
        now = now or time.time()
        # Clean expired penalties
        self.penalized_symbols = {s: exp for s, exp in self.penalized_symbols.items() if exp > now}

        if not trades:
            self.last_reflection_summary = "NO_TRADES (Waiting for data)"
            return self.last_reflection_summary

        recent = trades[-20:]
        loss_counts: Dict[str, int] = {}
        win_counts: Dict[str, int] = {}

        for t in reversed(recent):
            sym = t.get("symbol", "")
            pnl = t.get("pnl_usd", 0.0)
            if pnl < 0:
                loss_counts[sym] = loss_counts.get(sym, 0) + 1
            else:
                win_counts[sym] = win_counts.get(sym, 0) + 1

        penalized = []
        for sym, losses in loss_counts.items():
            wins = win_counts.get(sym, 0)
            if losses >= 2 and wins == 0:
                self.penalized_symbols[sym] = now + self.penalty_duration
                penalized.append(sym)

        self.last_reflection_summary = (
            f"REFLECTED ({len(recent)} trades): {len(penalized)} symbols penalized "
            f"({', '.join(penalized) if penalized else 'None'})"
        )
        return self.last_reflection_summary

    def is_symbol_permitted(self, symbol: str, now: float = None) -> Tuple[bool, str]:
        """Checks if symbol is currently penalized by the meta-critic."""
        now = now or time.time()
        expiry = self.penalized_symbols.get(symbol, 0.0)
        if expiry > now:
            remaining_m = (expiry - now) / 60.0
            return False, f"CRITIC_PENALTY (Symbol {symbol} locked for {remaining_m:.1f}m due to repeat losses)"
        return True, "CRITIC_OK"

    def get_penalized_symbols(self, now: float = None) -> Set[str]:
        now = now or time.time()
        return {s for s, exp in self.penalized_symbols.items() if exp > now}
