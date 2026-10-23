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

    def record_trade(self, symbol: str, pnl_pct: float, pnl_usd: float, reason: str) -> None:
        self.trades.append({
            "symbol": symbol,
            "pnl_pct": pnl_pct,
            "pnl_usd": pnl_usd,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc),
        })

    def check_hourly_snapshot(self, current_balance: float) -> None:
        elapsed_hours = int((datetime.now(timezone.utc) - self.start_time).total_seconds() // 3600)
        if elapsed_hours > self._last_snapshot_hour:
            self._last_snapshot_hour = elapsed_hours
            hour_trades = [
                t for t in self.trades
                if (elapsed_hours - 1) * 3600 <= (t["timestamp"] - self.start_time).total_seconds() < elapsed_hours * 3600
            ]
            hour_pnl = sum(t["pnl_usd"] for t in hour_trades)
            self.hourly_snapshots.append({
                "hour": elapsed_hours,
                "balance": round(current_balance, 2),
                "total_trades": len(hour_trades),
                "hour_pnl_usd": round(hour_pnl, 4),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M"),
            })

    def get_summary(self, current_balance: float) -> Dict[str, Any]:
        self.check_hourly_snapshot(current_balance)
        now = datetime.now(timezone.utc)
        elapsed_mins = round((now - self.start_time).total_seconds() / 60, 1)
        wins = sum(1 for t in self.trades if t["pnl_pct"] > 0)
        losses = sum(1 for t in self.trades if t["pnl_pct"] < 0)
        realized_pnl_usd = sum(t["pnl_usd"] for t in self.trades)
        total_pnl_usd = round(current_balance - self.initial_balance, 4)
        total_pnl_pct = round((total_pnl_usd / self.initial_balance) * 100, 2)
        win_rate = round((wins / len(self.trades) * 100), 1) if self.trades else 0.0

        return {
            "initial_balance": self.initial_balance,
            "current_balance": round(current_balance, 2),
            "realized_pnl_usd": round(realized_pnl_usd, 4),
            "total_pnl_usd": total_pnl_usd,
            "total_pnl_pct": total_pnl_pct,
            "total_trades": len(self.trades),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "elapsed_minutes": elapsed_mins,
            "elapsed_hours_str": f"{int(elapsed_mins // 60)}h {int(elapsed_mins % 60)}m",
            "hourly_snapshots": self.hourly_snapshots[-8:],
        }

    @staticmethod
    def translate_reason(reason: str) -> str:
        if "MANUAL_CLOSE" in reason:
            return "✋ إغلاق يدوي فوري من لوحة التحكم بطلب المستخدم"
        if "STOP_LOSS" in reason:
            return "🛑 ضرب وقف الخسارة الصارم (-0.9%) لحماية رأس المال بعد انعكاس السعر"
        if "TRAILING_TP" in reason:
            return "🎯 جني أرباح متحرك (+1.2%+) بعد ملاحقة القمة والارتداد"
        if "PARTIAL_TP_50" in reason:
            return "💰 جني أرباح جزئي 50% وتأمين نصف رأس المال"
        if "BREAKEVEN_EXIT" in reason:
            return "🛡️ خروج بحجز التعادل وتغطية الرسوم (+0.2%+)"
        if "DORMANT" in reason:
            return "💤 تسييل مبكر (الدقيقة 12) لركود السعر وتوفير السيولة"
        if "TIMEOUT" in reason:
            return "⏳ خروج زمني بعد انتهاء المهلة وتحرير الكاش"
        if "VOLUME_DECAY" in reason:
            return "📉 خروج استباقي بسبب جفاف أحجام التداول (>75%)"
        return reason
