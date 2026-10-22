"""Fast Offline Backtester & Strategy Optimizer: Simulates spot scalping across historical candles."""
from typing import List, Dict, Any


class FastBacktester:
    def __init__(self, initial_capital: float = 15.0, slot_size: float = 5.0, fee_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.slot_size = slot_size
        self.fee_rate = fee_rate

    def simulate_symbol(
        self, symbol: str, klines: List[Dict[str, Any]],
        min_score: float = 75.0, sl_pct: float = 0.009, tp_pct: float = 0.012
    ) -> List[Dict[str, Any]]:
        """Simulates entries and ladder exits on historical 1m klines."""
        trades = []
        in_pos = False
        entry_p, highest_p, entry_i = 0.0, 0.0, 0

        for i in range(20, len(klines)):
            c = float(klines[i].get("close", 0.0))
            if not in_pos:
                prev_vols = [float(k.get("volume", 0.0)) for k in klines[i-10:i]]
                avg_v = sum(prev_vols) / len(prev_vols) if prev_vols else 1.0
                c_vol = float(klines[i].get("volume", 0.0))
                ret_5m = (c - float(klines[i-5]["close"])) / float(klines[i-5]["close"]) if float(klines[i-5]["close"]) > 0 else 0.0
                score = min(100.0, (c_vol / max(1e-6, avg_v)) * 30.0 + (ret_5m * 1000.0) + 40.0)

                if score >= min_score and ret_5m > 0.002:
                    in_pos, entry_p, highest_p, entry_i = True, c, c, i
            else:
                bar_high = float(klines[i].get("high", c))
                bar_low = float(klines[i].get("low", c))
                highest_p = max(highest_p, bar_high)
                gain_high = (highest_p - entry_p) / entry_p
                gain_low = (bar_low - entry_p) / entry_p
                elapsed = i - entry_i

                stop_pct = -sl_pct
                if gain_high >= 0.020:
                    stop_pct = 0.015
                elif gain_high >= 0.012:
                    stop_pct = 0.008
                elif gain_high >= 0.006:
                    stop_pct = 0.002

                should_exit = False
                reason = "HOLD"
                exit_price = c

                if gain_low <= stop_pct:
                    should_exit, reason = True, "STOP_OR_RATCHET"
                    exit_price = round(entry_p * (1.0 + stop_pct), 6)
                elif gain_high >= tp_pct:
                    should_exit, reason = True, "TAKE_PROFIT"
                    exit_price = round(entry_p * (1.0 + tp_pct), 6)
                elif elapsed >= 20:
                    should_exit, reason = True, "TIMEOUT"
                    exit_price = c

                if should_exit:
                    actual_gain = (exit_price - entry_p) / entry_p
                    net_pnl = (actual_gain - (self.fee_rate * 2)) * self.slot_size
                    trades.append({
                        "symbol": symbol, "entry_price": entry_p, "exit_price": exit_price,
                        "pnl_usd": round(net_pnl, 4), "pnl_pct": round(actual_gain * 100, 2),
                        "duration_mins": elapsed, "reason": reason
                    })
                    in_pos = False

        return trades

    def evaluate_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not trades:
            return {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "net_pnl_usd": 0.0, "profit_factor": 0.0}
        wins = [t for t in trades if t["pnl_usd"] > 0]
        losses = [t for t in trades if t["pnl_usd"] < 0]
        gross_win = sum(t["pnl_usd"] for t in wins)
        gross_loss = abs(sum(t["pnl_usd"] for t in losses))
        pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
        return {
            "total_trades": len(trades), "wins": len(wins), "losses": len(losses),
            "win_rate": round(len(wins) / len(trades) * 100, 1),
            "net_pnl_usd": round(sum(t["pnl_usd"] for t in trades), 4),
            "profit_factor": pf
        }
