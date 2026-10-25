"""Meta-Critic Reflection Engine: Synthesizes trade logs into dynamic heuristics & blacklists."""
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set


class MetaCritic:
    def __init__(self, penalty_duration_sec: float = 3600.0, state_file: str = "data/critic_state.json"):
        self.penalty_duration = penalty_duration_sec
        self.state_file = Path(state_file)
        self.penalized_symbols: Dict[str, float] = {}
        self.last_reflection_summary = "INITIALIZED"
        self.load()

    def reflect_on_history(self, trades: List[Dict[str, Any]], now: float = None) -> str:
        now = now or time.time()
        self.penalized_symbols = {s: exp for s, exp in self.penalized_symbols.items() if exp > now}
        if not trades:
            self.last_reflection_summary = "NO_TRADES (Waiting for data)"
            return self.last_reflection_summary

        recent = trades[-20:]
        loss_counts, win_counts = {}, {}
        for t in reversed(recent):
            sym, pnl = t.get("symbol", ""), t.get("pnl_usd", 0.0)
            if pnl < 0:
                loss_counts[sym] = loss_counts.get(sym, 0) + 1
            else:
                win_counts[sym] = win_counts.get(sym, 0) + 1

        penalized = []
        for sym, losses in loss_counts.items():
            if losses >= 2 and win_counts.get(sym, 0) == 0:
                self.penalized_symbols[sym] = now + self.penalty_duration
                penalized.append(sym)

        self.last_reflection_summary = (
            f"REFLECTED ({len(recent)} trades): {len(penalized)} symbols penalized "
            f"({', '.join(penalized) if penalized else 'None'})"
        )
        self.save()
        return self.last_reflection_summary

    def is_symbol_permitted(self, symbol: str, now: float = None) -> Tuple[bool, str]:
        now = now or time.time()
        expiry = self.penalized_symbols.get(symbol, 0.0)
        if expiry > now:
            rem = (expiry - now) / 60.0
            return False, f"CRITIC_PENALTY (Symbol {symbol} locked for {rem:.1f}m due to repeat losses)"
        return True, "CRITIC_OK"

    def get_penalized_symbols(self, now: float = None) -> Set[str]:
        now = now or time.time()
        return {s for s, exp in self.penalized_symbols.items() if exp > now}

    def save(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.penalized_symbols, f)
        except Exception: pass

    def load(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self.penalized_symbols = json.load(f)
            except Exception: pass
