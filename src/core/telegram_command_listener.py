"""Telegram Interactive Command Listener: 2-way mobile control for trading bot."""
import logging
import threading
import time
import requests
from typing import Optional

logger = logging.getLogger("TelegramListener")


class TelegramCommandListener:
    def __init__(self, bot_token: Optional[str], chat_id: Optional[str], worker):
        self.bot_token = bot_token
        self.chat_id = str(chat_id) if chat_id else None
        self.worker = worker
        self.offset = 0
        self.running = False

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def _reply(self, text: str) -> None:
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=4)
        except Exception as e:
            logger.debug("Failed sending Telegram reply: %s", e)

    def handle_command(self, cmd: str) -> str:
        cmd = cmd.strip().lower()
        if cmd in ("/status", "status", "الحالة"):
            s = self.worker.snapshot()
            p = s.get("performance", {})
            return (f"📊 *حالة المنظومة الحالية*\n"
                    f"▫️ *الوضع:* `{s.get('mode')}` | *النشاط:* `{'نشط' if s.get('is_active') else 'متوقف'}`\n"
                    f"▫️ *الرصيد:* `${s.get('usdt_balance', 0):.2f}` USDT\n"
                    f"▫️ *الصفقات المفتوحة:* `{len(s.get('open_positions', []))}`\n"
                    f"▫️ *نسبة النجاح:* `{p.get('win_rate', 0)}%` (ربح: `${p.get('total_pnl_usd', 0):.2f}`)")
        elif cmd in ("/close_all", "close_all", "اغلاق_الكل"):
            res = self.worker.close_all()
            return f"🛑 *تم إغلاق الصفقات وإيقاف الدخول*\nالحالة: `{res.get('status')}`"
        elif cmd in ("/pause", "pause", "ايقاف"):
            self.worker.set_active(False)
            return "⏸️ *تم إيقاف فتح صفقات جديدة بنجاح.*"
        elif cmd in ("/resume", "resume", "استئناف"):
            self.worker.set_active(True)
            return "▶️ *تم استئناف البحث والدخول في الصفقات.*"
        elif cmd in ("/autopsy", "autopsy", "تشريح"):
            from src.core.session_autopsy import SessionAutopsy
            rep = SessionAutopsy.analyze_session(getattr(self.worker, 'trade_history', []))
            return (f"🩺 *التشريح الجنائي للجلسة*\n"
                    f"▫️ *الصفقات:* `{rep.get('total_trades', 0)}` (فوز: `{rep.get('wins', 0)}` / خسارة: `{rep.get('losses', 0)}`)\n"
                    f"▫️ *التوصية:* {rep.get('recommendation', 'لا توجد توصية')}")
        return ("🤖 *أوامر التحكم المتاحة:*\n"
                "`/status` - فحص الرصيد والصفقات\n"
                "`/close_all` - إغلاق الطوارئ وسحب الكاش\n"
                "`/pause` - إيقاف الدخول مؤقتاً\n"
                "`/resume` - استئناف الدخول\n"
                "`/autopsy` - تقرير التشخيص الذاتي")

    def start(self) -> None:
        if not self.is_configured:
            return
        self.running = True
        def _loop():
            while self.running:
                try:
                    url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
                    res = requests.get(url, params={"offset": self.offset, "timeout": 4}, timeout=6)
                    if res.status_code == 200:
                        for u in res.json().get("result", []):
                            self.offset = u["update_id"] + 1
                            msg = u.get("message", {})
                            sender = str(msg.get("chat", {}).get("id", ""))
                            if sender == self.chat_id and "text" in msg:
                                reply_text = self.handle_command(msg["text"])
                                self._reply(reply_text)
                except Exception:
                    time.sleep(2)
        threading.Thread(target=_loop, daemon=True, name="TelegramListener").start()
