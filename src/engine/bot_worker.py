"""Trading owner: serialize execution, persist intents and expose cached status."""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from src.config import config
from src.core.audit_journal import AuditJournal
from src.core.cooldown_manager import CooldownManager
from src.core.performance_tracker import PerformanceTracker
from src.core.state_store import StateStore
from src.core.telegram_notifier import TelegramNotifier
from src.core.volume_decay_exit import VolumeDecayExitDetector
from src.engine.worker_cycle import WorkerCycleMixin
from src.engine.worker_order_ops import WorkerOrderOpsMixin
from src.engine.worker_snapshot import WorkerSnapshotMixin
from src.engine.worker_state import WorkerState


class BotWorker(WorkerSnapshotMixin, WorkerOrderOpsMixin, WorkerCycleMixin, WorkerState):
    def __init__(self, exchange, allocator, regime_detector, scoring_engine,
                 risk_manager, news_fetcher, store=None, journal=None, mode=None):
        self.exchange, self.allocator = exchange, allocator
        self.regime_detector, self.scoring_engine = regime_detector, scoring_engine
        self.risk_manager, self.news_fetcher = risk_manager, news_fetcher
        self.mode = mode or config.trading_mode
        self.store = store
        self.lock = threading.RLock()
        self.snapshot_lock = threading.Lock()
        self.positions, self.pending_orders, self.cooldowns = {}, {}, {}
        self.trade_history, self.latest_news, self.entry_times, self.candidates = [], [], [], []
        self.last_error, self.last_step, self.errors = '', None, []
        self.stale_symbols = set()
        self.loss_limit_hit = self.storage_failed = False
        self.is_active = self.mode == 'PAPER'
        self.cash = float(exchange.get_balance('USDT'))
        self.tracker = PerformanceTracker(max(self.cash, 0.01))
        self.journal = journal if journal is not None else AuditJournal()
        self.volume_decay_detector = VolumeDecayExitDetector(min_retention_ratio=0.10, min_elapsed_minutes=14.0)
        self.cooldown_mgr = CooldownManager(default_cooldown_minutes=15.0)
        self.exchange._cooldown_mgr = self.cooldown_mgr
        self.notifier = TelegramNotifier(getattr(config, "telegram_bot_token", None), getattr(config, "telegram_chat_id", None))
        self.exchange._notifier = self.notifier
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='market-data')
        self.news_future = None
        self.last_news_poll = 0.0
        self._snapshot = {}
        self.restore()
        self.cash = float(exchange.get_balance('USDT'))
        self._publish()

    def error(self, message: str) -> None:
        self.last_error = message
        self.errors.append({'time': datetime.now(timezone.utc).isoformat(), 'message': message})
        del self.errors[:-20]

    def _record(self, trade: dict) -> None:
        self.tracker.record_trade(trade['symbol'], trade['pnl_pct'], trade['pnl_usd'], trade['reason'])
        self.cooldowns[trade['symbol']] = time.time() + config.symbol_cooldown_minutes * 60
        self.persist()
        try:
            self.journal.log_trade_closed(trade, self.cash)
        except OSError:
            self.error('تعذر تحديث سجل النص؛ بيانات التنفيذ محفوظة في ملف الحالة')

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
