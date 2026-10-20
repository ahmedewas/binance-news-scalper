"""Audit journal logger persisting real-time trade proof, Binance links, and daily PnL."""
import os
from datetime import datetime, timezone
from typing import Dict, Any


class AuditJournal:
    def __init__(self, file_path: str = "TRADING_JOURNAL.md"):
        self.file_path = file_path
        self._ensure_header()

    def _ensure_header(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write("# سجل التدقيق وتنفيذ الصفقات — راجع وضع PAPER/LIVE في لوحة التحكم\n\n")
                f.write("> هذا الملف يوثق لحظياً كل صفقة وبياناتها الحية المقروءة من بينانس للتحقق.\n\n---\n")

    def log_trade_opened(self, p: Dict[str, Any], reason: str, score: float, regime: str) -> None:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        clean_sym = p["symbol"].replace("/", "_")
        binance_url = f"https://www.binance.com/en/trade/{clean_sym}?type=spot"
        entry = (
            f"\n### 🟢 فتح صفقة جديدة: `{p['symbol']}` (خانة {p.get('slot_id', 1)})\n"
            f"- **التوقيت:** `{now_str}`\n"
            f"- **سعر الدخول المسجل:** `${p['entry_price']}`\n"
            f"- **رأس المال المخصص:** `${p.get('cost_basis', 5.0)}` USDT\n"
            f"- **رابط التحقق المباشر من بينانس:** [فتح شارت العملة على بينانس]({binance_url})\n"
            f"- **أسباب وتفاصيل الدخول:**\n"
            f"  - **الخبر / المحفز:** {reason}\n"
            f"  - **مرحلة السوق (Wyckoff):** `{regime}`\n"
            f"  - **درجة الإشارة (ليست احتمال نجاح):** `{score:.1f}/100`\n"
            f"- **الهدف الأولي (+1.2%):** `${p.get('target_tp', 0)}` | **الوقف الأولي (-0.9%):** `${p.get('stop_loss', 0)}`\n"
            f"---\n"
        )
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(entry)

    def log_trade_closed(self, t: Dict[str, Any], balance_after: float) -> None:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        pnl_sign = "+" if t["pnl_pct"] >= 0 else ""
        icon = "🎯" if t["pnl_pct"] >= 0 else "🛑"
        entry = (
            f"\n### {icon} إغلاق صفقة: `{t['symbol']}` | النتيجة: `{pnl_sign}{t['pnl_pct']}%` (${pnl_sign}{t['pnl_usd']})\n"
            f"- **توقيت الخروج:** `{now_str}` (مدة الصفقة: `{t.get('duration_mins', 0)}` دقيقة)\n"
            f"- **سعر الدخول:** `${t['entry_price']}` ⬅️ **سعر الخروج الحقيقي:** `${t['exit_price']}`\n"
            f"- **سبب الخروج الموثق:** {t.get('reason_arabic', t.get('reason', ''))}\n"
            f"- **الرصيد بعد الإغلاق:** `${balance_after:.2f}` USDT\n"
            f"---\n"
        )
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(entry)

    def read_journal(self) -> str:
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                return f.read()
        return "لا توجد سجلات بعد."
