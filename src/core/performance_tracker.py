"""Performance and hourly snapshot tracking for the trading session."""
from datetime import datetime, timezone
from typing import Dict, List, Any


class PerformanceTracker:
    def __init__(self, initial_balance: float = 15.0):
        self.initial_balance = float(initial_balance)
        self.start_time = datetime.now(timezone.utc)
        self.trades: List[Dict[str, Any]] = []
        self.hourly_snapshots: List[Dict[str, Any]] = []
        self._last_snapshot_hour = 0

    def record_trade(self, symbol: str, pnl_pct: float, pnl_usd: float, reason: str, fee: float = 0.0) -> None:
        self.trades.append({"symbol": symbol, "pnl_pct": pnl_pct, "pnl_usd": pnl_usd,
                            "reason": reason, "fee_quote": fee, "timestamp": datetime.now(timezone.utc)})

    def check_hourly_snapshot(self, current_balance: float) -> None:
        elapsed_hours = int((datetime.now(timezone.utc) - self.start_time).total_seconds() // 3600)
        if elapsed_hours > self._last_snapshot_hour:
            self._last_snapshot_hour = elapsed_hours
            hour_trades = [t for t in self.trades if (elapsed_hours - 1) * 3600 <= (t["timestamp"] - self.start_time).total_seconds() < elapsed_hours * 3600]
            self.hourly_snapshots.append({
                "hour": elapsed_hours, "balance": round(current_balance, 2), "total_trades": len(hour_trades),
                "hour_pnl_usd": round(sum(t["pnl_usd"] for t in hour_trades), 4), "timestamp": datetime.now(timezone.utc).strftime("%H:%M"),
            })

    def get_summary(self, current_balance: float) -> Dict[str, Any]:
        self.check_hourly_snapshot(current_balance)
        now = datetime.now(timezone.utc)
        elapsed_mins = round((now - self.start_time).total_seconds() / 60, 1)
        w_t = [t for t in self.trades if t.get("pnl_usd", 0) > 0]
        l_t = [t for t in self.trades if t.get("pnl_usd", 0) < 0]
        realized = round(sum(t["pnl_usd"] for t in self.trades), 4)
        total_pnl = round(current_balance - self.initial_balance, 4)
        g_w, g_l = sum(t["pnl_usd"] for t in w_t), abs(sum(t["pnl_usd"] for t in l_t))
        return {
            "initial_balance": self.initial_balance, "current_balance": round(current_balance, 2),
            "realized_pnl_usd": realized, "unrealized_pnl_usd": round(total_pnl - realized, 4),
            "total_fees_usd": round(sum(t.get("fee_quote", 0.0) for t in self.trades), 4),
            "total_pnl_usd": total_pnl, "total_pnl_pct": round((total_pnl / self.initial_balance) * 100, 2),
            "total_trades": len(self.trades), "wins": len(w_t), "losses": len(l_t),
            "win_rate": round(len(w_t) / len(self.trades) * 100, 1) if self.trades else 0.0,
            "profit_factor": round(g_w / g_l, 2) if g_l > 1e-6 else (99.0 if g_w > 0 else 0.0),
            "avg_win_usd": round(g_w / len(w_t), 4) if w_t else 0.0, "avg_loss_usd": round(g_l / len(l_t), 4) if l_t else 0.0,
            "elapsed_minutes": elapsed_mins, "elapsed_hours_str": f"{int(elapsed_mins // 60)}h {int(elapsed_mins % 60)}m",
            "hourly_snapshots": self.hourly_snapshots[-8:],
        }

    @staticmethod
    def translate_reason(reason: str) -> str:
        r = reason.upper()
        if "MANUAL_CLOSE" in r: return "✋ إغلاق يدوي فوري بطلب المستخدم"
        if "STOP_LOSS" in r: return "🛑 ضرب وقف الخسارة الصارم لحماية رأس المال"
        if "TRAILING_TP" in r: return "🎯 جني أرباح متحرك وملاحقة القمة"
        if "PARTIAL_TP" in r: return "💰 جني أرباح جزئي وتأمين الكاش"
        if "BREAKEVEN" in r: return "🛡️ خروج بحجز التعادل وتغطية الرسوم (+0.2%+)"
        if "DORMANT" in r: return "💤 تسييل لتوفير السيولة"
        if "TIMEOUT" in r: return "⏳ خروج زمني بعد انتهاء المهلة القصوى"
        if "VOLUME_DECAY" in r: return "📉 خروج استباقي بسبب جفاف أحجام التداول (>75%)"
        return reason
