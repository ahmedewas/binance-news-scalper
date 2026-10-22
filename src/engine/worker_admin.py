"""Worker Administrative Operations: Activation control, mode switching, and session resets."""
import uuid
from datetime import datetime, timezone
from src.config import config
from src.core.performance_tracker import PerformanceTracker
from src.core.state_store import StateStore


class WorkerAdminMixin:
    def set_active(self, active: bool) -> dict:
        with self.lock:
            if active and (self.pending_orders or self.storage_failed or self.loss_limit_hit):
                raise ValueError('التشغيل محظور: أمر غير محسوم أو عطل حفظ أو تجاوز حد خسارة الجلسة')
            if active and self.mode == 'LIVE':
                for p in self.positions.values():
                    available = self.exchange.get_balance(p.symbol.split('/')[0])
                    if available + max(1e-12, p.amount * 1e-8) < p.amount:
                        raise ValueError('رصيد المركز لا يطابق البورصة؛ راجع التسوية قبل التشغيل')
            self.is_active = bool(active)
            self.persist()
            self._publish()
            return {'is_active': self.is_active}

    def switch_mode(self, new_mode: str) -> dict:
        with self.lock:
            mode_upper = new_mode.upper()
            if mode_upper not in ('PAPER', 'LIVE'):
                raise ValueError('نمط التداول يجب أن يكون إما PAPER أو LIVE')
            if self.positions or self.pending_orders:
                raise ValueError('يجب إغلاق كافة الصفقات وتسوية الأوامر المعلقة قبل تغيير نمط التداول')
            if mode_upper == 'LIVE':
                if not (config.api_key and config.api_secret):
                    raise ValueError('مفاتيح بينانس API غير مدخلة في الإعدادات؛ لا يمكن بدء التداول الحقيقي')
                from src.exchange.live import LiveExchange
                self.exchange = LiveExchange(config.api_key, config.api_secret)
            else:
                from src.exchange.paper import PaperExchange
                self.exchange = PaperExchange(config.initial_paper_balance)
            self.mode = mode_upper
            self.cash = float(self.exchange.get_balance('USDT'))
            self.tracker = PerformanceTracker(self.cash)
            self.is_active = True
            self.persist()
            self._publish()
            return {'mode': self.mode, 'is_active': self.is_active, 'balance': self.cash}

    def reset_paper_session(self) -> dict:
        with self.lock:
            if self.mode != 'PAPER' or self.positions or self.pending_orders:
                raise ValueError('جلسة جديدة متاحة للمحاكاة فقط بعد إغلاق المراكز وتسوية الأوامر')
            self.is_active = False
            self.persist()
            if self.store:
                archive = self.store.path.parent / 'sessions' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.json')
                StateStore(archive).save(self.store.load())
            self.exchange.usdt_balance = config.initial_paper_balance
            self.exchange.holdings = {}
            self.cash = config.initial_paper_balance
            self.tracker = PerformanceTracker(self.cash)
            self.trade_history, self.latest_news, self.entry_times, self.candidates = [], [], [], []
            self.cooldowns = {}
            self.loss_limit_hit = False
            self.last_error, self.errors = '', []
            self.persist()
            self._publish()
            return {'status': 'NEW_PAPER_SESSION', 'is_active': False}
