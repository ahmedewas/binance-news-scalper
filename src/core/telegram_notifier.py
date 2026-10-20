"""Telegram Instant Alert Engine: Dispatches mobile trade and profit alerts asynchronously."""
import logging
import threading
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("TelegramNotifier")


class TelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage" if self.bot_token else None

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def _async_send(self, text: str) -> None:
        if not self.is_configured:
            return

        def _worker():
            try:
                payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
                requests.post(self.api_url, json=payload, timeout=4)
            except Exception as e:
                logger.debug("Telegram alert delivery failed: %s", e)

        threading.Thread(target=_worker, daemon=True, name="TelegramAlert").start()

    def notify_trade_opened(self, p: Dict[str, Any], reason: str, score: float) -> None:
        msg = (
            f"🟢 *صفقة جديدة مفتوحة: {p['symbol']}*\n"
            f"💵 *سعر الدخول:* `${p['entry_price']}`\n"
            f"🎯 *الهدف التقديري:* `${p.get('target_tp', 0)}` | *الوقف:* `${p.get('stop_loss', 0)}`\n"
            f"📊 *التقييم المؤسسي:* `{score:.1f}/100`\n"
            f"💡 *السبب:* {reason[:60]}"
        )
        self._async_send(msg)

    def notify_trade_closed(self, t: Dict[str, Any], balance: float) -> None:
        icon = "🎯" if t["pnl_pct"] >= 0 else "🛑"
        sign = "+" if t["pnl_pct"] >= 0 else ""
        msg = (
            f"{icon} *إغلاق صفقة: {t['symbol']}*\n"
            f"📈 *النتيجة:* `{sign}{t['pnl_pct']}%` (${sign}{t['pnl_usd']})\n"
            f"⏱️ *المدة:* `{t.get('duration_mins', 0)} دقيقة`\n"
            f"🔍 *السبب:* {t.get('reason_arabic', t.get('reason', ''))[:60]}\n"
            f"💰 *الرصيد بعد الإغلاق:* `${balance:.2f} USDT`"
        )
        self._async_send(msg)
