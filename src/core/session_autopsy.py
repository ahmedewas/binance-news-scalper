"""Automated Session Diagnostic & Autopsy: Analyzes trade patterns to recommend parameter tuning."""
from typing import List, Dict, Any


class SessionAutopsy:
    @staticmethod
    def analyze_session(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Performs forensic performance breakdown across all session trades."""
        if not trades:
            return {
                "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "net_pnl_usd": 0.0,
                "best_symbol": "None", "top_exit_reason": "None",
                "recommendation": "لا توجد صفقات مكتملة كافية بعد لإجراء الفحص الذاتي.",
            }

        wins = [t for t in trades if t.get("pnl_pct", 0) > 0]
        losses = [t for t in trades if t.get("pnl_pct", 0) < 0]
        total_pnl = sum(t.get("pnl_usd", 0.0) for t in trades)
        win_rate = round((len(wins) / len(trades)) * 100, 1)

        # Performance by symbol
        sym_pnl: Dict[str, float] = {}
        for t in trades:
            s = t.get("symbol", "")
            sym_pnl[s] = sym_pnl.get(s, 0.0) + t.get("pnl_usd", 0.0)

        best_sym = max(sym_pnl.items(), key=lambda x: x[1])[0] if sym_pnl else "None"

        # Exit reasons breakdown
        reason_counts: Dict[str, int] = {}
        for t in trades:
            r = t.get("reason_arabic") or t.get("reason", "OTHER")
            key = r[:35]
            reason_counts[key] = reason_counts.get(key, 0) + 1

        top_reason = max(reason_counts.items(), key=lambda x: x[1])[0] if reason_counts else "None"

        # Automated Diagnostic Recommendation
        if win_rate >= 60.0:
            rec = "أداء استثنائي متفوق؛ المنظومة تلتقط الزخم بدقة عالية وأهداف الـ ATR محققة."
        elif len(losses) > len(wins) and "جفاف أحجام" in top_reason:
            rec = "تنبيه: الخروج المبكر يستهلك العمولات؛ يُنصح بالاعتماد الصارم على وقف الخسارة وإعطاء الصفقات وقتاً للتنفس."
        else:
            rec = "المنظومة في وضع استقرار دفاعي؛ يُفضل رفع عتبة التقييم إلى 82 نقطة لتصفية الصفقات الضعيفة."

        return {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "net_pnl_usd": round(total_pnl, 4),
            "best_symbol": best_sym,
            "top_exit_reason": top_reason,
            "recommendation": rec,
        }
